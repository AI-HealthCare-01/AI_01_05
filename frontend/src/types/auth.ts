export interface KakaoLoginResponse {
  is_new_user: boolean
  access_token: string | null
  refresh_token: string | null
  temp_token: string | null
  kakao_info: { nickname: string | null } | null
}

export interface SignupRequest {
  nickname: string
  phone_number: string
  phone_verification_token: string
  email: string
  gender: string
  birthday: string | null
  agreements: {
    terms_of_service: boolean
    privacy_policy: boolean
    sensitive_policy: boolean
    sms_agreed: boolean
    terms_of_marketing: boolean
  }
}

export interface AgreementState {
  terms_of_service: boolean
  privacy_policy: boolean
  sensitive_policy: boolean
  sms_agreed: boolean
  terms_of_marketing: boolean
  all: boolean
}

export interface PhoneSendResponse {
  ttl: number
  message: string
}

export interface PhoneVerifyResponse {
  verification_token: string
  message: string
}
