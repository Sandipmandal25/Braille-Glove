#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <freertos/queue.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ── UUIDs (must match backend/ble/gatt.py) ───────────────────────────────────
#define SERVICE_UUID        "a1b2c3d4-0001-4e5f-8000-000000000001"
#define HAPTIC_CHAR_UUID    "a1b2c3d4-0001-4e5f-8000-000000000002"
#define BUTTON_CHAR_UUID    "a1b2c3d4-0001-4e5f-8000-000000000003"

// ── Pin assignments ───────────────────────────────────────────────────────────
const uint8_t SOLENOID_PINS[6] = {13, 12, 14, 27, 26, 25};  // dots 1-6
const uint8_t DOT_PINS[6]      = { 4, 16, 17, 18, 19, 21};  // dot buttons 1-6
const uint8_t PIN_PREV         = 22;
const uint8_t PIN_NEXT         = 23;
const uint8_t PIN_ENTER        = 32;

// ── Timing ────────────────────────────────────────────────────────────────────
#define DEBOUNCE_MS      50
#define DOUBLE_TAP_MS   350   // max gap between taps to count as double

// ── Button packet encoding (matches backend/ble/protocol.py) ─────────────────
#define BTN_BRAILLE  0x0
#define BTN_PREV     0x1
#define BTN_NEXT     0x2
#define BTN_ENTER    0x3
#define EVT_SINGLE   0x0
#define EVT_DOUBLE   0x1

// ── BLE globals ───────────────────────────────────────────────────────────────
BLEServer         *pServer        = nullptr;
BLECharacteristic *pHapticChar    = nullptr;
BLECharacteristic *pButtonChar    = nullptr;
bool               deviceConnected = false;

// ── Haptic queue (BLE task enqueues, loop() drains — no blocking delay) ──────
struct HapticCmd {
    uint8_t  mask;
    uint32_t duration_ms;
};

static QueueHandle_t hapticQueue    = nullptr;
static bool          hapticActive   = false;
static uint32_t      hapticStartMs  = 0;
static uint32_t      hapticDuration = 0;

// ── Button state ──────────────────────────────────────────────────────────────
struct NavButtonState {
    uint8_t  pin;
    uint8_t  btnType;
    bool     lastRaw;
    uint32_t lastChangeMs;
    uint32_t lastTapMs;
    uint8_t  tapCount;
};

NavButtonState navButtons[3] = {
    {PIN_PREV,  BTN_PREV,  HIGH, 0, 0, 0},
    {PIN_NEXT,  BTN_NEXT,  HIGH, 0, 0, 0},
    {PIN_ENTER, BTN_ENTER, HIGH, 0, 0, 0},
};

// Dot buttons: chord fires when all dots released together
bool     dotLastRaw[6]  = {HIGH, HIGH, HIGH, HIGH, HIGH, HIGH};
bool     dotPressed[6]  = {false};
uint32_t dotChangeMs[6] = {0};
bool     chordActive    = false;
uint8_t  chordMask      = 0;

// ── BLE callbacks ─────────────────────────────────────────────────────────────
class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer *) override {
        deviceConnected = true;
        Serial.println("[BLE] Client connected");
    }
    void onDisconnect(BLEServer *s) override {
        deviceConnected = false;
        Serial.println("[BLE] Client disconnected — restarting advertising");
        s->startAdvertising();
    }
};

class HapticCallbacks : public BLECharacteristicCallbacks {
    // Runs on BLE task — must not block. Push to queue and return immediately.
    void onWrite(BLECharacteristic *c) override {
        std::string val = c->getValue();
        if (val.length() < 2) return;

        HapticCmd cmd = {
            .mask        = (uint8_t)val[0],
            .duration_ms = (uint32_t)(uint8_t)val[1] * 10
        };
        // Non-blocking send — drop silently if queue is full
        xQueueSend(hapticQueue, &cmd, 0);
    }
};

// ── Send helpers ──────────────────────────────────────────────────────────────
void sendNavPacket(uint8_t btnType, uint8_t evtType) {
    if (!deviceConnected) return;
    uint8_t pkt = (btnType << 4) | (evtType & 0x0F);
    pButtonChar->setValue(&pkt, 1);
    pButtonChar->notify();
    Serial.printf("[BTN] type=0x%X evt=0x%X pkt=0x%02X\n", btnType, evtType, pkt);
}

void sendBraillePacket(uint8_t mask) {
    if (!deviceConnected) return;
    uint8_t pkt[2] = {0x00, (uint8_t)(mask & 0x3F)};
    pButtonChar->setValue(pkt, 2);
    pButtonChar->notify();
    Serial.printf("[BTN] BRAILLE mask=0x%02X\n", mask);
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);  // disable brownout for USB-powered testing
    Serial.begin(115200);

    // Solenoids — all off at start
    for (int i = 0; i < 6; i++) {
        pinMode(SOLENOID_PINS[i], OUTPUT);
        digitalWrite(SOLENOID_PINS[i], LOW);
    }

    // Dot buttons (internal pull-up, active LOW)
    for (int i = 0; i < 6; i++) {
        pinMode(DOT_PINS[i], INPUT_PULLUP);
    }

    // Nav buttons (internal pull-up, active LOW)
    for (auto &b : navButtons) {
        pinMode(b.pin, INPUT_PULLUP);
    }

    // Haptic command queue — 32 slots (covers a full long message)
    hapticQueue = xQueueCreate(32, sizeof(HapticCmd));

    // BLE init
    BLEDevice::init("BrailleGlove");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());

    BLEService *pService = pServer->createService(SERVICE_UUID);

    // HAPTIC_OUTPUT — writable by host
    pHapticChar = pService->createCharacteristic(
        HAPTIC_CHAR_UUID,
        BLECharacteristic::PROPERTY_WRITE
    );
    pHapticChar->setCallbacks(new HapticCallbacks());

    // BUTTON_INPUT — notifies host
    pButtonChar = pService->createCharacteristic(
        BUTTON_CHAR_UUID,
        BLECharacteristic::PROPERTY_NOTIFY
    );
    pButtonChar->addDescriptor(new BLE2902());

    pService->start();

    BLEAdvertising *pAdv = BLEDevice::getAdvertising();
    pAdv->addServiceUUID(SERVICE_UUID);
    pAdv->setScanResponse(true);
    BLEDevice::startAdvertising();

    Serial.println("[BLE] Advertising as 'BrailleGlove'");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
    uint32_t now = millis();

    // ── Haptic drain (non-blocking millis-based) ─────────────────────────────
    if (hapticActive) {
        if (now - hapticStartMs >= hapticDuration) {
            for (int i = 0; i < 6; i++) {
                digitalWrite(SOLENOID_PINS[i], LOW);
            }
            hapticActive = false;
        }
    } else {
        HapticCmd cmd;
        if (xQueueReceive(hapticQueue, &cmd, 0) == pdTRUE) {
            for (int i = 0; i < 6; i++) {
                digitalWrite(SOLENOID_PINS[i], (cmd.mask & (1 << i)) ? HIGH : LOW);
            }
            hapticStartMs  = now;
            hapticDuration = cmd.duration_ms;
            hapticActive   = true;
            Serial.printf("[HAPTIC] mask=0x%02X dur=%ums\n", cmd.mask, cmd.duration_ms);
        }
    }

    // ── Dot buttons (chord detection) ────────────────────────────────────────
    bool anyDotHeld = false;
    for (int i = 0; i < 6; i++) {
        bool raw = digitalRead(DOT_PINS[i]);

        if (raw != dotLastRaw[i] && (now - dotChangeMs[i]) > DEBOUNCE_MS) {
            dotLastRaw[i]  = raw;
            dotChangeMs[i] = now;
            dotPressed[i]  = (raw == LOW);
        }

        if (dotPressed[i]) {
            anyDotHeld = true;
            chordMask |= (1 << i);
            chordActive = true;
        }
    }

    // Chord fires on full release of all dot buttons
    if (chordActive && !anyDotHeld) {
        sendBraillePacket(chordMask);
        chordMask   = 0;
        chordActive = false;
    }

    // ── Nav buttons (PREV / NEXT / ENTER) ────────────────────────────────────
    for (auto &b : navButtons) {
        bool raw = digitalRead(b.pin);

        if (raw != b.lastRaw && (now - b.lastChangeMs) > DEBOUNCE_MS) {
            b.lastRaw      = raw;
            b.lastChangeMs = now;

            if (raw == LOW) {
                b.tapCount++;
                b.lastTapMs = now;
            }
        }

        // Flush after double-tap window expires
        if (b.tapCount > 0 && (now - b.lastTapMs) > DOUBLE_TAP_MS) {
            uint8_t evt = (b.tapCount >= 2) ? EVT_DOUBLE : EVT_SINGLE;
            sendNavPacket(b.btnType, evt);
            b.tapCount = 0;
        }
    }
}
