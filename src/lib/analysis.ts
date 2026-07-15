/* ═══════════════════════════════════════════════════════
   약봉투 이미지 분석 — 파이썬 DDI API 연동
   서버: 앱 개발/server.py 의 POST /analyze-image
   (사진 → OCR → inference.py analyze() → 식별/상호작용/위험도)
   환경변수 PUBLIC_ANALYZE_API 가 비어 있으면 목업으로 데모.
   ═══════════════════════════════════════════════════════ */
import { env } from '$env/dynamic/public';

/** 식별된 약 1건 (inference.py get_info + fuzzy 정보) */
export interface IdentifiedInfo {
	id: string; // 성분명(ingredient)
	max_dose_mg_day: number | null;
	max_duration_days: number | null;
	fuzzy_matched?: boolean;
	match_score?: number;
	matched_alias?: string;
	llm_matched?: boolean; // DB·fuzzy로 못 찾아 Gemini로 폴백 매칭된 경우
}

/** 성분쌍 상호작용 1건 */
export interface Interaction {
	drug_a: string;
	drug_b: string;
	source: 'DUR' | 'DDInter' | 'model' | string;
	severity: string; // contraindicated | major | moderate | minor | predicted
	risk_score: number;
	description: string;
}

export interface FuzzyCandidate {
	alias: string;
	ingredient: string;
	match_score: number;
	match_method: string;
}
export interface Unidentified {
	raw: string;
	normalized: string;
	fuzzy_candidates: FuzzyCandidate[];
}

/** analyze() 전체 결과 */
export interface AnalyzeResult {
	identified: Record<string, IdentifiedInfo>; // 원본 약품명 → 정보
	unidentified: Unidentified[];
	interactions: Interaction[];
	drug_risk_score: number; // 0~1
	ocr_lines?: string[];
}

const API = (env.PUBLIC_ANALYZE_API ?? '').replace(/\/$/, '');

/** 1일 복용 횟수 → 추천 시간대 (일정 제안 기본값) */
export function slotsFor(timesPerDay: number | undefined): string[] {
	switch (timesPerDay) {
		case 1:
			return ['morning'];
		case 2:
			return ['morning', 'evening'];
		case 4:
			return ['morning', 'noon', 'evening', 'night'];
		default:
			return ['morning', 'noon', 'evening'];
	}
}

/** 위험도 등급 (배너 표시용) */
export function riskLevel(r: AnalyzeResult): {
	label: string;
	tone: 'low' | 'warn' | 'danger';
} {
	const contra = r.interactions.some((i) => i.severity === 'contraindicated');
	if (contra || r.drug_risk_score >= 0.7) return { label: '주의가 필요해요', tone: 'danger' };
	if (r.drug_risk_score >= 0.3) return { label: '함께 복용 시 주의하세요', tone: 'warn' };
	return { label: '특별한 위험은 낮아요', tone: 'low' };
}

const SEV_KO: Record<string, string> = {
	contraindicated: '병용금기',
	major: '주의 높음',
	moderate: '주의 중간',
	minor: '주의 낮음',
	predicted: 'AI 추정'
};
export const severityKo = (s: string) => SEV_KO[s] ?? s;
export function severityTone(s: string): 'danger' | 'warn' | 'low' {
	if (s === 'contraindicated' || s === 'major') return 'danger';
	if (s === 'moderate' || s === 'predicted') return 'warn';
	return 'low';
}

/**
 * 여러 약을 각각 여러 장 찍어 보낸다. 약(버스트)마다 서버가 다수결 OCR로
 * 정확도를 높인 뒤, 전체를 합쳐 상호작용까지 분석한다.
 * bursts: 약별 사진 배열 (bursts[i] = i번째 약의 사진 dataURL 목록)
 *
 * 서버는 HF Spaces 의 Gradio 앱이므로 Gradio REST 2-step 으로 호출한다:
 *   1) POST /gradio_api/call/analyze_images  → event_id
 *   2) GET  /gradio_api/call/analyze_images/{event_id}  (SSE) → 완료 시 결과
 */
export async function analyzeImages(bursts: string[][]): Promise<AnalyzeResult> {
	if (!API) return mockResult();
	const items = bursts.map((images) => ({ images }));

	// 1) 호출 시작 → event_id
	const start = await fetch(`${API}/gradio_api/call/analyze_images`, {
		method: 'POST',
		headers: { 'content-type': 'application/json' },
		body: JSON.stringify({ data: [items] })
	});
	if (!start.ok) throw new Error(`analyze failed: ${start.status}`);
	const { event_id } = (await start.json()) as { event_id: string };

	// 2) 결과 스트림 수신 (완료되면 스트림이 닫히며 text 가 확정됨)
	const res = await fetch(`${API}/gradio_api/call/analyze_images/${event_id}`);
	if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
	const text = await res.text();

	// SSE 본문에서 마지막 유효한 "data: [...]" 줄이 최종 출력
	let payload: unknown[] | null = null;
	for (const line of text.split('\n')) {
		if (!line.startsWith('data:')) continue;
		try {
			const parsed = JSON.parse(line.slice(5).trim());
			if (Array.isArray(parsed) && parsed.length) payload = parsed;
		} catch {
			/* heartbeat 등 무시 */
		}
	}
	if (!payload) throw new Error('analyze: empty response');
	return payload[0] as AnalyzeResult;
}

/** 서버 연결 전 데모용 목업 (실제 응답과 같은 형태) */
function mockResult(): AnalyzeResult {
	return {
		identified: {
			'아모크라정 625mg': { id: '아목시실린/클라불란산', max_dose_mg_day: 1875, max_duration_days: 14 },
			록소프로펜나트륨정: { id: '록소프로펜', max_dose_mg_day: 180, max_duration_days: null },
			알마겔정: { id: '알마게이트', max_dose_mg_day: null, max_duration_days: null }
		},
		unidentified: [
			{
				raw: '리자벨정',
				normalized: '리자벨',
				fuzzy_candidates: [
					{ alias: '리자트립탄', ingredient: '리자트립탄', match_score: 0.82, match_method: 'sequence_matcher' }
				]
			}
		],
		interactions: [
			{
				drug_a: '록소프로펜',
				drug_b: '알마게이트',
				source: 'DDInter',
				severity: 'moderate',
				risk_score: 0.45,
				description: '제산제가 소염진통제 흡수를 늦출 수 있어요'
			}
		],
		drug_risk_score: 0.45
	};
}
