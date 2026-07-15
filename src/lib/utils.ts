/* 날짜·표기 헬퍼 */

export const DAY_NAMES = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일'];
export const DAY_NAMES_SHORT = ['일', '월', '화', '수', '목', '금', '토'];

/** 로컬 기준 'YYYY-MM-DD' */
export function dateKey(d: Date = new Date()): string {
	const y = d.getFullYear();
	const m = String(d.getMonth() + 1).padStart(2, '0');
	const day = String(d.getDate()).padStart(2, '0');
	return `${y}-${m}-${day}`;
}

export function todayKey(): string {
	return dateKey(new Date());
}

/** '26.06.11' 스타일 헤더 표기 */
export function fmtHeader(key: string): string {
	const [y, m, d] = key.split('-');
	return `${y.slice(2)}.${m}.${d}`;
}

export function dayName(key: string): string {
	return DAY_NAMES[parseKey(key).getDay()];
}

export function parseKey(key: string): Date {
	const [y, m, d] = key.split('-').map(Number);
	return new Date(y, m - 1, d);
}

/** 복용 시간대 (icon = Icon.svelte의 name) */
export interface Slot {
	id: string;
	label: string;
	time: string; // 대표 시각 (정렬·"다음 복용" 계산용)
}
export const SLOTS: Slot[] = [
	{ id: 'morning', label: '아침', time: '08:00' },
	{ id: 'noon', label: '점심', time: '12:30' },
	{ id: 'evening', label: '저녁', time: '18:30' },
	{ id: 'night', label: '자기 전', time: '22:00' }
];
export const slotLabel = (id: string) => SLOTS.find((s) => s.id === id)?.label ?? id;

/** 약 색상 팔레트 (선택용) */
export const MED_COLORS = [
	{ id: 'blue', bg: '#e8f3ff', fg: '#3182f6' },
	{ id: 'red', bg: '#fdedee', fg: '#f04452' },
	{ id: 'green', bg: '#e5f9f0', fg: '#02b262' },
	{ id: 'orange', bg: '#fff3e0', fg: '#f57c00' },
	{ id: 'purple', bg: '#f3e8ff', fg: '#8b5cf6' },
	{ id: 'gray', bg: '#f2f4f6', fg: '#4e5968' }
];
export const medColor = (id: string) => MED_COLORS.find((c) => c.id === id) ?? MED_COLORS[0];

/** 시간대별 인사말 */
export function greeting(): string {
	const h = new Date().getHours();
	if (h < 5) return '늦은 밤이에요';
	if (h < 11) return '좋은 아침이에요';
	if (h < 17) return '좋은 오후예요';
	if (h < 22) return '좋은 저녁이에요';
	return '오늘 하루 수고했어요';
}
