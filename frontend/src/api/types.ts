export type LoginRequestDto = {
  username: string
  password: string
}

export type LoginResponseDto = {
  access_token: string
  token_type: string
  expires_at: string
  user_id: string
  display_name: string | null
}

export type StandardTermDto = {
  id: string
  category: string
  value: string
  display_order: number
  is_active: boolean
  usage_count: number
}

export type TermUpdateRequestDto = {
  value?: string
  display_order?: number
  is_active?: boolean
}
