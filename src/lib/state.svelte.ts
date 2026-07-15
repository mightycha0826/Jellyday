/* ═══════════════════════════════════════════════════════
   Jellyday — 전역 상태 (Svelte 5 runes)
   낙관적 로컬 갱신 → Supabase write-through
   ═══════════════════════════════════════════════════════ */
import type { Session } from '@supabase/supabase-js';
import { supabase, hasSupabase } from './supabase';
import { todayKey, parseKey } from './utils';

/* ── types ── */
export interface Profile {
	id: string;
	email: string | null;
	nick: string;
}
export interface Medication {
	id: string;
	name: string;
	dosage: string;
	times: string[]; // morning | noon | evening | night
	days_of_week: number[]; // 0(일)~6(토)
	start_date: string;
	end_date: string | null;
	color: string;
	memo: string;
}
export interface MedLog {
	id: string;
	medication_id: string;
	date: string; // YYYY-MM-DD
	time_slot: string;
}

/* ── state ── */
export const S = $state({
	booted: false,
	session: null as Session | null,
	profile: null as Profile | null,
	meds: [] as Medication[],
	logs: [] as MedLog[],
	logMonths: [] as string[], // 로그가 로드된 'YYYY-MM' 목록
	toasts: [] as { id: number; msg: string }[],
	// PWA 설치
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	installEvt: null as any, // beforeinstallprompt 이벤트
	installed: false
});

export const UI = $state({
	addChooserOpen: false, // "약 추가하기" → 직접/촬영 선택 시트
	medFormOpen: false,
	editingMed: null as Medication | null,
	presetName: '' // 카메라 식별 결과 → 약 추가 폼 프리셋
});

/* ── toast ── */
let toastSeq = 0;
export function toast(msg: string) {
	const id = ++toastSeq;
	S.toasts.push({ id, msg });
	setTimeout(() => {
		S.toasts = S.toasts.filter((t) => t.id !== id);
	}, 2400);
}

/* ── PWA 설치 ── */
export async function installApp() {
	const e = S.installEvt as {
		prompt: () => void;
		userChoice: Promise<{ outcome: string }>;
	} | null;
	if (!e) {
		// beforeinstallprompt 미지원(iOS Safari 등) 또는 아직 준비 안 됨
		toast('브라우저 메뉴에서 "홈 화면에 추가"를 선택해 주세요');
		return;
	}
	e.prompt();
	try {
		const { outcome } = await e.userChoice;
		if (outcome === 'accepted') S.installed = true;
	} catch {
		/* 사용자가 닫음 */
	}
	S.installEvt = null;
}

/* ── boot ── */
export async function init() {
	if (S.booted) return;
	if (!hasSupabase) {
		S.booted = true;
		return;
	}
	const { data } = await supabase.auth.getSession();
	S.session = data.session;
	supabase.auth.onAuthStateChange((_e, sess) => {
		const was = S.session?.user.id;
		S.session = sess;
		if (sess && sess.user.id !== was) void loadAll();
		if (!sess) {
			S.profile = null;
			S.meds = [];
			S.logs = [];
			S.logMonths = [];
		}
	});
	// 로그인 화면 없음 — 세션이 없으면 익명 세션 자동 생성
	// (Supabase Dashboard > Authentication에서 Anonymous sign-ins 활성화 필요)
	if (S.session) {
		await loadAll();
	} else {
		const { error } = await supabase.auth.signInAnonymously();
		if (error) toast('저장소 연결에 실패했어요');
	}
	S.booted = true;
}

async function loadAll() {
	const uid = S.session?.user.id;
	if (!uid) return;
	const ym = todayKey().slice(0, 7);
	const [p, m] = await Promise.all([
		supabase.from('profiles').select('*').eq('id', uid).single(),
		supabase.from('medications').select('*').order('created_at')
	]);
	if (p.data) S.profile = p.data as Profile;
	S.meds = (m.data ?? []) as Medication[];
	S.logMonths = [];
	S.logs = [];
	await loadMonth(ym);
}

/** 해당 월('YYYY-MM')의 복용 로그 로드 (중복 로드 방지) */
export async function loadMonth(ym: string) {
	if (!S.session || S.logMonths.includes(ym)) return;
	S.logMonths.push(ym);
	const [y, m] = ym.split('-').map(Number);
	const next = m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`;
	const { data } = await supabase
		.from('medication_logs')
		.select('id, medication_id, date, time_slot')
		.gte('date', `${ym}-01`)
		.lt('date', `${next}-01`);
	if (data) {
		const ids = new Set(S.logs.map((l) => l.id));
		S.logs.push(...(data as MedLog[]).filter((l) => !ids.has(l.id)));
	}
}

/* ── 복용 체크 토글 (낙관적) ── */
export async function toggleLog(medId: string, date: string, slot: string) {
	const found = S.logs.find(
		(l) => l.medication_id === medId && l.date === date && l.time_slot === slot
	);
	// 세션 없음(환경변수 미설정 등) — 화면에서만 동작, 저장 안 됨
	if (!S.session) {
		if (found) S.logs = S.logs.filter((l) => l.id !== found.id);
		else S.logs.push({ id: crypto.randomUUID(), medication_id: medId, date, time_slot: slot });
		return;
	}
	if (found) {
		S.logs = S.logs.filter((l) => l.id !== found.id);
		const { error } = await supabase.from('medication_logs').delete().eq('id', found.id);
		if (error) {
			S.logs.push(found);
			toast('저장에 실패했어요');
		}
	} else {
		const tmp: MedLog = {
			id: `tmp-${Date.now()}`,
			medication_id: medId,
			date,
			time_slot: slot
		};
		S.logs.push(tmp);
		const { data, error } = await supabase
			.from('medication_logs')
			.insert({ user_id: S.session!.user.id, medication_id: medId, date, time_slot: slot })
			.select('id')
			.single();
		if (error || !data) {
			S.logs = S.logs.filter((l) => l.id !== tmp.id);
			toast('저장에 실패했어요');
		} else {
			const row = S.logs.find((l) => l.id === tmp.id);
			if (row) row.id = data.id;
		}
	}
}

export function isTaken(medId: string, date: string, slot: string): boolean {
	return S.logs.some((l) => l.medication_id === medId && l.date === date && l.time_slot === slot);
}

/* ── 약 CRUD ── */
export async function saveMed(
	input: Omit<Medication, 'id'>,
	id?: string
): Promise<boolean> {
	if (!S.session) {
		if (id) {
			const prev = S.meds.find((m) => m.id === id);
			if (prev) Object.assign(prev, input);
		} else {
			S.meds.push({ ...input, id: crypto.randomUUID() });
		}
		return true;
	}
	if (id) {
		const prev = S.meds.find((m) => m.id === id);
		if (!prev) return false;
		Object.assign(prev, input);
		const { error } = await supabase.from('medications').update(input).eq('id', id);
		if (error) {
			toast('저장에 실패했어요');
			return false;
		}
	} else {
		const { data, error } = await supabase
			.from('medications')
			.insert({ ...input, user_id: S.session!.user.id })
			.select('*')
			.single();
		if (error || !data) {
			toast('저장에 실패했어요');
			return false;
		}
		S.meds.push(data as Medication);
	}
	return true;
}

export async function deleteMed(id: string) {
	const prev = S.meds;
	S.meds = S.meds.filter((m) => m.id !== id);
	S.logs = S.logs.filter((l) => l.medication_id !== id);
	if (!S.session) return;
	const { error } = await supabase.from('medications').delete().eq('id', id);
	if (error) {
		S.meds = prev;
		toast('삭제에 실패했어요');
	}
}

export async function updateNick(nick: string) {
	if (!S.profile) return;
	S.profile.nick = nick;
	if (!S.session) return;
	await supabase.from('profiles').update({ nick }).eq('id', S.profile.id);
}

/* ── 파생 헬퍼 ── */

/** 해당 날짜에 복용 중인 약 */
export function medsOn(date: string): Medication[] {
	const dow = parseKey(date).getDay();
	return S.meds.filter(
		(m) =>
			m.times.length > 0 &&
			m.days_of_week.includes(dow) &&
			m.start_date <= date &&
			(!m.end_date || m.end_date >= date)
	);
}

/** 해당 날짜의 (약 × 시간대) 총 복용 건수와 완료 건수 */
export function dayProgress(date: string): { total: number; done: number } {
	let total = 0;
	let done = 0;
	for (const m of medsOn(date)) {
		for (const slot of m.times) {
			total++;
			if (isTaken(m.id, date, slot)) done++;
		}
	}
	return { total, done };
}
