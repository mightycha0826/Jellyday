import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { env } from '$env/dynamic/public';

// 구형(anon key, eyJ...)·신형(publishable key, sb_publishable_...) 키 이름 모두 지원
const url = env.PUBLIC_SUPABASE_URL ?? '';
const key = env.PUBLIC_SUPABASE_ANON_KEY ?? env.PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? '';

export const hasSupabase = url.startsWith('http') && key.length > 20;

// 환경변수가 비어 있으면 로그인 화면에서 설정 안내를 띄운다 (supabase는 null)
export const supabase: SupabaseClient = hasSupabase
	? createClient(url, key)
	: (null as unknown as SupabaseClient);
