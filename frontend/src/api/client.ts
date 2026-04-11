export interface DeviceStatusResponse {
  connected:        boolean
  mode:             string
  queue_length:     number
  cursor_position:  number
  unread_count:     number
  compose_slot:     number
  compose_text:     string
}

export interface MessageResponse {
  id:          number
  external_id: string
  sender_id:   string
  sender_name: string
  text:        string
  status:      string
  timestamp:   number
}

export interface MessageListResponse {
  items: MessageResponse[]
  total: number
}

export interface FavoriteResponse {
  slot:        number
  name:        string
  telegram_id: string
}

const BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status}: ${body || res.statusText}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  device: {
    status:     () => request<DeviceStatusResponse>('/device/status'),
    connect:    () => request<{ status: string }>('/device/connect',    { method: 'POST' }),
    disconnect: () => request<{ status: string }>('/device/disconnect', { method: 'POST' }),
  },

  messages: {
    list:     (status?: string) =>
      request<MessageListResponse>(`/messages${status ? `?status=${status}` : ''}`),
    markRead: (id: number) =>
      request<MessageResponse>(`/messages/${id}/read`, { method: 'POST' }),
    delete:   (id: number) =>
      request<void>(`/messages/${id}`, { method: 'DELETE' }),
  },

  contacts: {
    list:   () => request<FavoriteResponse[]>('/contacts'),
    upsert: (slot: number, body: { name: string; telegram_id: string }) =>
      request<FavoriteResponse>(`/contacts/${slot}`, {
        method: 'PUT',
        body:   JSON.stringify(body),
      }),
    delete: (slot: number) =>
      request<void>(`/contacts/${slot}`, { method: 'DELETE' }),
  },

  testing: {
    inject: (body: { sender_name: string; sender_id: string; text: string }) =>
      request<{ status: string }>('/test/inject', {
        method: 'POST',
        body:   JSON.stringify(body),
      }),
    button: (body: { button: string; event: string; dot_mask?: number }) =>
      request<{ status: string; mode: string }>('/test/button', {
        method: 'POST',
        body:   JSON.stringify(body),
      }),
    selectContact: (slot: number) =>
      request<{ status: string; mode: string }>(`/test/select_contact/${slot}`, { method: 'POST' }),
  },
}
