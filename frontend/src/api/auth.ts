import { apiRequest } from './http'
import type { LoginRequestDto, LoginResponseDto } from './types'

export function login(body: LoginRequestDto) {
  return apiRequest<LoginResponseDto>('/auth/login', {
    method: 'POST',
    body,
  })
}
