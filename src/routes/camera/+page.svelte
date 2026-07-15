<script lang="ts">
	import { goto } from '$app/navigation';
	import BottomSheet from '$lib/components/BottomSheet.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { saveMed, toast } from '$lib/state.svelte';
	import { SLOTS, MED_COLORS, dateKey, todayKey } from '$lib/utils';
	import {
		analyzeImages,
		slotsFor,
		riskLevel,
		severityKo,
		severityTone,
		type AnalyzeResult,
		type IdentifiedInfo
	} from '$lib/analysis';

	let videoEl: HTMLVideoElement | undefined = $state();
	let stream: MediaStream | null = null;
	let ready = $state(false);
	let denied = $state(false);
	let facing = $state<'environment' | 'user'>('environment');
	let flash = $state(false); // 촬영 피드백
	let fileInput: HTMLInputElement | undefined = $state(); // 갤러리 선택용 input
	let rotate = $state(0); // 0 | 90 | 180 | 270 — 촬영 방향(가로/세로)
	let camW = $state(0);
	let camH = $state(0);
	// 90/270도 회전 시 프리뷰가 화면을 꽉 채우도록 확대 비율
	const coverScale = $derived(
		rotate % 180 === 0 || !camW || !camH ? 1 : Math.max(camW, camH) / Math.min(camW, camH)
	);

	// shoot: 촬영 중 / choice: 완료 후 선택 / analyzing·result·failed: 결과 시트
	let phase = $state<'shoot' | 'choice' | 'analyzing' | 'result' | 'failed'>('shoot');
	let shots = $state<string[]>([]); // 현재 약의 버스트
	let bursts = $state<string[][]>([]); // 완료된 약들
	let showModal = $state(false); // 첫 안내 모달
	let hideGuide = $state(false); // "오늘 하루 보지 않기"

	// 결과 편집
	let result = $state<AnalyzeResult | null>(null);
	let picked = $state<Set<number>>(new Set());
	let slots = $state<string[]>([]);
	let adding = $state(false);
	let sheetOpen = $state(false);

	// 결과 시트를 닫으면(딤/ESC) 처음부터 다시
	$effect(() => {
		if (!sheetOpen && phase !== 'shoot' && phase !== 'choice') reset();
	});

	$effect(() => {
		hideGuide = localStorage.getItem('pill.camGuideHide') === todayKey();
	});

	async function start() {
		stop();
		ready = false;
		denied = false;
		try {
			stream = await navigator.mediaDevices.getUserMedia({
				video: {
					facingMode: { ideal: facing },
					// 고해상도 요청 — 지원 범위 내에서 최대한 크게 (ideal 이라 없으면 자동 하향)
					width: { ideal: 2560 },
					height: { ideal: 1440 }
				},
				audio: false
			});
			if (videoEl) {
				videoEl.srcObject = stream;
				await videoEl.play();
			}
			ready = true;
		} catch {
			denied = true;
		}
	}
	function stop() {
		stream?.getTracks().forEach((t) => t.stop());
		stream = null;
	}
	$effect(() => {
		void facing;
		void start();
		return stop;
	});

	// 캡처 공통: 소스를 긴 변 최대 2560px, JPEG 0.92 로 그려 dataURL 생성
	// (해상도를 크게 확보하되 업로드/처리 크기는 합리적으로 — OCR엔 2560이면 충분)
	const MAX_LONG = 2560;
	function drawToDataUrl(src: CanvasImageSource, w: number, h: number, rot = 0): string {
		const scale = Math.min(1, MAX_LONG / Math.max(w, h));
		const sw = Math.max(1, Math.round(w * scale));
		const sh = Math.max(1, Math.round(h * scale));
		const swap = rot % 180 !== 0; // 90/270도는 가로·세로가 바뀜
		const c = document.createElement('canvas');
		c.width = swap ? sh : sw;
		c.height = swap ? sw : sh;
		const ctx = c.getContext('2d')!;
		ctx.translate(c.width / 2, c.height / 2);
		ctx.rotate((rot * Math.PI) / 180);
		ctx.drawImage(src, -sw / 2, -sh / 2, sw, sh);
		return c.toDataURL('image/jpeg', 0.92);
	}
	function blip() {
		flash = true;
		setTimeout(() => (flash = false), 140);
	}

	// 갤러리에서 사진 선택 — 촬영과 동일하게 현재 약(shots)에 추가
	function pickImage() {
		fileInput?.click();
	}
	function onPickFile(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		for (const file of Array.from(input.files ?? [])) {
			const url = URL.createObjectURL(file);
			const img = new Image();
			img.onload = () => {
				shots = [...shots, drawToDataUrl(img, img.naturalWidth, img.naturalHeight)];
				URL.revokeObjectURL(url);
			};
			img.src = url;
		}
		input.value = ''; // 같은 파일을 다시 선택할 수 있도록 초기화
	}

	// 셔터 — 현재 약에 사진 한 장 추가
	async function shoot() {
		if (!ready) return;
		const track = stream?.getVideoTracks()[0];
		// 1) ImageCapture: 카메라 센서의 최대 해상도로 스틸 촬영 (프리뷰보다 훨씬 선명).
		//    Chrome/Android 지원. 실패하거나 미지원(iOS)이면 아래 폴백.
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const IC = (globalThis as any).ImageCapture;
		if (track && IC) {
			try {
				const blob: Blob = await new IC(track).takePhoto();
				const bmp = await createImageBitmap(blob);
				shots = [...shots, drawToDataUrl(bmp, bmp.width, bmp.height, rotate)];
				bmp.close();
				blip();
				return;
			} catch {
				/* 폴백으로 진행 */
			}
		}
		// 2) 폴백: 고해상도 비디오 프레임 캡처 (iOS 등)
		if (videoEl?.videoWidth) {
			shots = [...shots, drawToDataUrl(videoEl, videoEl.videoWidth, videoEl.videoHeight, rotate)];
			blip();
		}
	}

	// [완료] — 현재 약 촬영 종료 → 선택 단계
	function finishMed() {
		if (shots.length === 0) return;
		showModal = !hideGuide;
		phase = 'choice';
	}

	// [약 추가] — 현재 약을 담고 다음 약 촬영
	function addMore() {
		bursts = [...bursts, shots];
		shots = [];
		showModal = false;
		phase = 'shoot';
	}

	// [약 확인하기] — 지금까지 담은 약 전체 분석
	async function confirmNow() {
		const all = shots.length ? [...bursts, shots] : bursts;
		bursts = all;
		shots = [];
		showModal = false;
		if (all.length === 0) return;

		phase = 'analyzing';
		sheetOpen = true;
		try {
			const r = await analyzeImages(all);
			result = r;
			const entries = Object.entries(r.identified);
			picked = new Set(entries.map((_, i) => i));
			slots = slotsFor(undefined);
			phase = 'result';
		} catch {
			phase = 'failed';
		}
	}

	function dismissGuideToday() {
		localStorage.setItem('pill.camGuideHide', todayKey());
		hideGuide = true;
		showModal = false;
	}

	// 처음부터 다시
	function reset() {
		shots = [];
		bursts = [];
		result = null;
		sheetOpen = false;
		phase = 'shoot';
	}

	function togglePick(i: number) {
		const next = new Set(picked);
		if (next.has(i)) next.delete(i);
		else next.add(i);
		picked = next;
	}
	function toggleSlot(id: string) {
		slots = slots.includes(id) ? slots.filter((s) => s !== id) : [...slots, id];
	}

	const entries = $derived<[string, IdentifiedInfo][]>(
		result ? Object.entries(result.identified) : []
	);
	const inters = $derived(
		result ? [...result.interactions].sort((a, b) => b.risk_score - a.risk_score) : []
	);
	const risk = $derived(result ? riskLevel(result) : null);

	const startDate = $derived(todayKey());
	const suggestDays = $derived.by(() => {
		const ds = entries
			.map(([, v]) => v.max_duration_days)
			.filter((d): d is number => typeof d === 'number' && d > 0);
		return ds.length ? Math.min(...ds) : null;
	});
	const endDate = $derived.by(() => {
		if (!suggestDays) return null;
		const d = new Date();
		d.setDate(d.getDate() + suggestDays - 1);
		return dateKey(d);
	});

	function doseHint(v: IdentifiedInfo): string {
		const parts: string[] = [v.id];
		if (v.max_dose_mg_day) parts.push(`1일 최대 ${v.max_dose_mg_day}mg`);
		if (v.max_duration_days) parts.push(`최대 ${v.max_duration_days}일`);
		return parts.join(' · ');
	}

	async function addPicked() {
		if (!result || picked.size === 0 || slots.length === 0 || adding) return;
		adding = true;
		let ok = 0;
		for (const [i, [raw, info]] of entries.entries()) {
			if (!picked.has(i)) continue;
			const done = await saveMed({
				name: raw,
				dosage: '',
				times: slots,
				days_of_week: [0, 1, 2, 3, 4, 5, 6],
				start_date: startDate,
				end_date: endDate,
				color: MED_COLORS[i % MED_COLORS.length].id,
				memo: doseHint(info)
			});
			if (done) ok++;
		}
		adding = false;
		if (ok > 0) {
			toast(`약 ${ok}개를 추가했어요`);
			void goto('/');
		}
	}

</script>

<div class="cam" bind:clientWidth={camW} bind:clientHeight={camH}>
	<!-- svelte-ignore a11y_media_has_caption -->
	<video
		class="feed"
		bind:this={videoEl}
		playsinline
		muted
		style="transform: rotate({rotate}deg) scale({coverScale});"
	></video>
	{#if flash}<div class="flash" aria-hidden="true"></div>{/if}

	{#if denied}
		<div class="denied">
			<span aria-hidden="true">📷</span>
			<h2>카메라를 사용할 수 없어요</h2>
			<p>브라우저 설정에서 카메라 권한을<br />허용한 뒤 다시 시도해 주세요</p>
			<button class="btn ghost retry" onclick={start}>다시 시도</button>
		</div>
	{:else if phase === 'shoot'}
		<div class="guide" aria-hidden="true">
			<i></i>
			<p>같은 약을 여러 장 찍을수록 정확해져요</p>
		</div>
	{/if}

	<button class="back" onclick={() => goto('/')} aria-label="뒤로가기">
		<svg viewBox="0 0 24 24"><path d="M15 5.5 8.5 12l6.5 6.5" /></svg>
	</button>

	{#if phase === 'shoot' && !denied}
		<button
			class="rotate"
			onclick={() => (rotate = (rotate + 90) % 360)}
			aria-label="촬영 방향 회전 (가로/세로)"
		>
			<svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-2.6-6.4" /><path d="M21 4v5h-5" /></svg>
		</button>
	{/if}

	<!-- 진행 상태 -->
	{#if bursts.length > 0 && phase !== 'result'}
		<div class="progress">담은 약 {bursts.length}개</div>
	{/if}

	<!-- 하단 컨트롤 -->
	{#if phase === 'shoot'}
		{#if shots.length > 0}
			<div class="shotcount">이 약 {shots.length}장 촬영됨</div>
		{/if}
		<div class="ctrl">
			<button class="side" onclick={pickImage} aria-label="갤러리에서 사진 선택">
				<svg viewBox="0 0 24 24">
					<rect x="3" y="3" width="18" height="18" rx="2.5" />
					<circle cx="9" cy="9" r="2" />
					<path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21" />
				</svg>
			</button>
			<input
				class="filepick"
				type="file"
				accept="image/*"
				multiple
				bind:this={fileInput}
				onchange={onPickFile}
			/>
			<button class="shutter" onclick={shoot} disabled={!ready} aria-label="촬영"><i></i></button>
			{#if shots.length > 0}
				<button class="done" onclick={finishMed}>완료</button>
			{:else}
				<button
					class="side"
					onclick={() => (facing = facing === 'environment' ? 'user' : 'environment')}
					aria-label="카메라 전환"
				>
					<svg viewBox="0 0 24 24"
						><path d="M4 9a8 8 0 0 1 13.7-3M20 15a8 8 0 0 1-13.7 3" /><path
							d="M17.5 2.5 18 6l-3.5.6M6.5 21.5 6 18l3.5-.6"
						/></svg
					>
				</button>
			{/if}
		</div>
	{:else if phase === 'choice' && !showModal}
		<!-- 안내를 끈 뒤: 카메라 위 두 박스 -->
		<div class="choice">
			<button class="cbox" onclick={confirmNow}>
				<b>약 확인하기</b><span>지금 결과 보기</span>
			</button>
			<button class="cbox add" onclick={addMore}>
				<b>약 추가</b><span>다른 약 더 찍기</span>
			</button>
		</div>
	{/if}
</div>

<!-- 첫 안내 모달 -->
{#if phase === 'choice' && showModal}
	<div class="mdim" aria-hidden="true"></div>
	<div class="modal" role="dialog" aria-modal="true" aria-label="촬영 안내">
		<div class="m-emoji" aria-hidden="true">💊📷</div>
		<h2>다 찍으셨나요?</h2>
		<p>
			같은 약을 <b>여러 장</b> 찍을수록 더 정확해요. 다른 약이 더 있으면
			<b>약 추가</b>로 이어 찍고, 다 찍었으면 <b>약 확인하기</b>를 눌러 한 번에 확인하세요.
		</p>
		<div class="m-actions">
			<button class="btn ghost" onclick={addMore}>약 추가</button>
			<button class="btn" onclick={confirmNow}>약 확인하기</button>
		</div>
		<button class="m-dismiss" onclick={dismissGuideToday}>오늘 하루 보지 않기</button>
	</div>
{/if}

<BottomSheet bind:open={sheetOpen} title={phase === 'result' ? '알 수 있는 정보' : ''}>
	{#if phase === 'analyzing'}
		<div class="anal">
			<div class="spinner big-spin" aria-hidden="true"></div>
			<h2>약봉투를 읽고 있어요</h2>
			<p>여러 장을 비교해 약과 상호작용을 확인하는 중이에요</p>
		</div>
	{:else if phase === 'failed' || !result}
		<div class="anal">
			<span class="big" aria-hidden="true">😵</span>
			<h2>분석하지 못했어요</h2>
			<p>글자가 잘 보이게 다시 찍어주세요</p>
			<button class="btn ghost" style="margin-top: 18px" onclick={reset}>다시 촬영하기</button>
		</div>
	{:else}
		{#if risk}
			<div class="risk tone-{risk.tone}">
				<span class="risk-icon" aria-hidden="true">
					{#if risk.tone === 'low'}
						<svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
					{:else}
						<svg viewBox="0 0 24 24"
							><path d="M12 3 22 20H2Z" /><line x1="12" y1="10" x2="12" y2="14" /><circle
								cx="12"
								cy="17"
								r="0.6"
							/></svg
						>
					{/if}
				</span>
				<div>
					<p class="risk-label">{risk.label}</p>
					<p class="risk-sub">식별 {entries.length}개 · 상호작용 {inters.length}건</p>
				</div>
			</div>
		{/if}

		{#if inters.length > 0}
			<h3 class="sub">함께 복용 시 주의</h3>
			<div class="inters">
				{#each inters as it (it.drug_a + it.drug_b)}
					<div class="inter tone-{severityTone(it.severity)}">
						<span class="sev">{severityKo(it.severity)}</span>
						<div class="inter-body">
							<p class="pair">{it.drug_a} <em>✕</em> {it.drug_b}</p>
							<p class="desc">{it.description}</p>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<h3 class="sub">봉투에서 찾은 약 {entries.length}개</h3>
		<div class="meds">
			{#each entries as [raw, info], i (raw)}
				<button
					class="med"
					class:on={picked.has(i)}
					onclick={() => togglePick(i)}
					aria-pressed={picked.has(i)}
				>
					<span class="mark" aria-hidden="true">
						<svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
					</span>
					<span class="mi">
						<span class="mn">{raw}</span>
						<span class="ms">{doseHint(info)}{info.fuzzy_matched ? ' · 유사 매칭' : ''}</span>
					</span>
				</button>
			{/each}
		</div>

		{#if result.unidentified.length > 0}
			<h3 class="sub">인식하지 못한 항목</h3>
			<div class="unk">
				{#each result.unidentified as u (u.raw)}
					<div class="unk-row">
						<span class="unk-name">{u.raw}</span>
						{#if u.fuzzy_candidates.length > 0}
							<span class="unk-guess">혹시 {u.fuzzy_candidates[0].alias}?</span>
						{/if}
					</div>
				{/each}
				<p class="unk-note">정확한 이름은 직접 추가할 수 있어요.</p>
			</div>
		{/if}

		{#if entries.length > 0}
			<h3 class="sub">이렇게 챙겨드릴게요</h3>
			<div class="plan">
				<div class="chips">
					{#each SLOTS as s (s.id)}
						<button
							class="chip"
							class:on={slots.includes(s.id)}
							onclick={() => toggleSlot(s.id)}
							aria-pressed={slots.includes(s.id)}
						>
							<Icon name={s.id} size={16} /> {s.label}
						</button>
					{/each}
				</div>
				<p class="period">
					{startDate.replaceAll('-', '.')} 부터
					{#if endDate}
						{' '}{endDate.replaceAll('-', '.')} 까지 ({suggestDays}일)
					{:else}
						{' '}계속
					{/if}
					· 매일 {slots.length}회
				</p>
			</div>

			<button
				class="btn"
				style="margin-top: 18px"
				disabled={picked.size === 0 || slots.length === 0 || adding}
				onclick={addPicked}
			>
				{adding ? '추가하는 중…' : `선택한 약 ${picked.size}개 추가하기`}
			</button>
		{/if}
		<button class="btn ghost" style="margin-top: 8px" onclick={reset}>다시 촬영하기</button>
		<p class="disclaim">자동 분석 결과예요. 정확한 복용은 약사·의사와 상의하세요.</p>
	{/if}
</BottomSheet>

<style>
	.cam {
		position: fixed;
		inset: 0;
		background: #101318;
		max-width: var(--maxw);
		margin: 0 auto;
		overflow: hidden;
	}
	.feed {
		width: 100%;
		height: 100%;
		object-fit: cover;
		transform-origin: center;
		transition: transform 0.3s ease;
	}
	.flash {
		position: absolute;
		inset: 0;
		background: #fff;
		animation: flashout 0.14s ease-out;
	}
	@keyframes flashout {
		from {
			opacity: 0.8;
		}
		to {
			opacity: 0;
		}
	}

	.guide {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 18px;
		pointer-events: none;
	}
	.guide i {
		width: min(78vw, 340px);
		aspect-ratio: 3 / 4;
		border: 2.5px solid rgba(255, 255, 255, 0.9);
		border-radius: 20px;
		box-shadow: 0 0 0 100vmax rgba(16, 19, 24, 0.35);
	}
	.guide p {
		color: rgba(255, 255, 255, 0.9);
		font-size: 14px;
		font-weight: 600;
	}

	.denied {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 6px;
		color: #fff;
		text-align: center;
	}
	.denied span {
		font-size: 40px;
		margin-bottom: 8px;
	}
	.denied h2 {
		font-size: 18px;
		font-weight: 700;
	}
	.denied p {
		font-size: 14px;
		color: rgba(255, 255, 255, 0.65);
	}
	.retry {
		width: auto;
		padding: 0 24px;
		height: 44px;
		margin-top: 16px;
		background: rgba(255, 255, 255, 0.12);
		color: #fff;
	}

	.back {
		position: absolute;
		top: calc(env(safe-area-inset-top) + 14px);
		left: 14px;
		width: 42px;
		height: 42px;
		border-radius: 50%;
		background: rgba(16, 19, 24, 0.5);
		backdrop-filter: blur(8px);
		color: #fff;
		display: grid;
		place-items: center;
	}
	.back svg,
	.rotate svg {
		width: 22px;
		height: 22px;
		fill: none;
		stroke: currentColor;
		stroke-width: 2.2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.rotate {
		position: absolute;
		top: calc(env(safe-area-inset-top) + 14px);
		right: 14px;
		width: 42px;
		height: 42px;
		border-radius: 50%;
		background: rgba(16, 19, 24, 0.5);
		backdrop-filter: blur(8px);
		color: #fff;
		display: grid;
		place-items: center;
	}
	.rotate:active {
		background: rgba(16, 19, 24, 0.8);
	}

	.progress {
		position: absolute;
		top: calc(env(safe-area-inset-top) + 20px);
		left: 50%;
		transform: translateX(-50%);
		background: rgba(16, 19, 24, 0.55);
		backdrop-filter: blur(8px);
		color: #fff;
		font-size: 13px;
		font-weight: 700;
		padding: 6px 14px;
		border-radius: 999px;
	}
	.shotcount {
		position: absolute;
		bottom: calc(env(safe-area-inset-bottom) + 128px);
		left: 50%;
		transform: translateX(-50%);
		background: rgba(49, 130, 246, 0.9);
		color: #fff;
		font-size: 13px;
		font-weight: 700;
		padding: 6px 14px;
		border-radius: 999px;
	}

	.ctrl {
		position: absolute;
		bottom: calc(env(safe-area-inset-bottom) + 32px);
		left: 0;
		right: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 36px;
	}
	.side {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.14);
		backdrop-filter: blur(8px);
		color: #fff;
		display: grid;
		place-items: center;
		transition: background 0.15s;
	}
	.side:disabled {
		opacity: 0.35;
	}
	.filepick {
		display: none;
	}
	.side svg {
		width: 22px;
		height: 22px;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.9;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.shutter {
		width: 74px;
		height: 74px;
		border-radius: 50%;
		border: 4px solid #fff;
		display: grid;
		place-items: center;
		background: transparent;
	}
	.shutter i {
		width: 58px;
		height: 58px;
		border-radius: 50%;
		background: #fff;
		transition: transform 0.12s;
	}
	.shutter:active i {
		transform: scale(0.85);
	}
	.shutter:disabled {
		opacity: 0.4;
	}
	.done {
		min-width: 60px;
		height: 48px;
		padding: 0 16px;
		border-radius: 24px;
		background: var(--blue);
		color: #fff;
		font-size: 15px;
		font-weight: 700;
	}
	.done:active {
		background: var(--blue-press);
	}

	/* 완료 후 선택 박스 */
	.choice {
		position: absolute;
		bottom: calc(env(safe-area-inset-bottom) + 28px);
		left: 20px;
		right: 20px;
		display: flex;
		gap: 10px;
	}
	.cbox {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		padding: 14px 16px;
		border-radius: 16px;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(8px);
		text-align: left;
	}
	.cbox b {
		font-size: 16px;
		font-weight: 700;
		color: var(--text);
	}
	.cbox span {
		font-size: 12px;
		color: var(--text-3);
	}
	.cbox.add {
		background: var(--blue);
	}
	.cbox.add b {
		color: #fff;
	}
	.cbox.add span {
		color: rgba(255, 255, 255, 0.85);
	}

	/* 첫 안내 모달 */
	.mdim {
		position: fixed;
		inset: 0;
		background: rgba(0, 23, 51, 0.5);
		z-index: 95;
	}
	.modal {
		position: fixed;
		left: 50%;
		bottom: 0;
		transform: translateX(-50%);
		width: 100%;
		max-width: var(--maxw);
		z-index: 96;
		background: var(--surface);
		border-radius: 24px 24px 0 0;
		padding: 26px 24px calc(env(safe-area-inset-bottom) + 18px);
		text-align: center;
		animation: up 0.3s cubic-bezier(0.22, 1, 0.36, 1) both;
	}
	@keyframes up {
		from {
			transform: translateX(-50%) translateY(100%);
		}
	}
	.m-emoji {
		font-size: 30px;
		margin-bottom: 8px;
	}
	.modal h2 {
		font-size: 19px;
		font-weight: 800;
		margin-bottom: 8px;
	}
	.modal p {
		font-size: 14px;
		color: var(--text-2);
		line-height: 1.6;
		margin-bottom: 20px;
	}
	.m-actions {
		display: flex;
		gap: 10px;
	}
	.m-actions .btn {
		flex: 1;
	}
	.m-dismiss {
		margin-top: 14px;
		float: left;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-3);
		padding: 4px 2px;
	}

	/* 결과 시트 */
	.anal {
		text-align: center;
		padding: 28px 0 20px;
	}
	.big-spin {
		width: 34px;
		height: 34px;
		margin: 0 auto 18px;
	}
	.anal h2 {
		font-size: 18px;
		font-weight: 700;
		margin-bottom: 4px;
	}
	.anal p {
		font-size: 14px;
		color: var(--text-3);
	}
	.big {
		font-size: 40px;
		display: block;
		margin-bottom: 10px;
	}

	.tone-low {
		--tc: var(--green);
		--tbg: var(--green-soft);
	}
	.tone-warn {
		--tc: #e8890c;
		--tbg: #fff3e0;
	}
	.tone-danger {
		--tc: var(--red);
		--tbg: var(--red-soft);
	}

	.risk {
		display: flex;
		align-items: center;
		gap: 12px;
		background: var(--tbg);
		border-radius: 16px;
		padding: 14px 16px;
		margin-bottom: 4px;
	}
	.risk-icon {
		flex: none;
		width: 34px;
		height: 34px;
		border-radius: 50%;
		background: var(--tc);
		display: grid;
		place-items: center;
	}
	.risk-icon svg {
		width: 20px;
		height: 20px;
		fill: none;
		stroke: #fff;
		stroke-width: 2.2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.risk-label {
		font-size: 16px;
		font-weight: 700;
		color: var(--tc);
	}
	.risk-sub {
		font-size: 13px;
		color: var(--text-3);
		margin-top: 1px;
	}

	.sub {
		font-size: 14px;
		font-weight: 700;
		color: var(--text-2);
		margin: 20px 0 8px;
	}

	.inters {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.inter {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		background: var(--tbg);
		border-radius: 14px;
		padding: 12px 14px;
	}
	.sev {
		flex: none;
		font-size: 12px;
		font-weight: 800;
		color: #fff;
		background: var(--tc);
		border-radius: 8px;
		padding: 3px 8px;
		margin-top: 1px;
	}
	.inter-body {
		min-width: 0;
	}
	.pair {
		font-size: 15px;
		font-weight: 700;
	}
	.pair em {
		font-style: normal;
		color: var(--tc);
		margin: 0 2px;
	}
	.desc {
		font-size: 13px;
		color: var(--text-2);
		margin-top: 2px;
	}

	.meds {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.med {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 14px;
		border-radius: 14px;
		background: var(--fill);
		border: 1.5px solid transparent;
		text-align: left;
		transition: all 0.15s;
	}
	.med.on {
		background: var(--blue-soft);
		border-color: var(--blue);
	}
	.mark {
		flex: none;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		background: var(--fill-strong);
		color: #fff;
		transition: background 0.15s;
	}
	.med.on .mark {
		background: var(--blue);
	}
	.mark svg {
		width: 14px;
		height: 14px;
		fill: none;
		stroke: currentColor;
		stroke-width: 2.6;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.mi {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}
	.mn {
		font-size: 15px;
		font-weight: 700;
	}
	.ms {
		font-size: 13px;
		color: var(--text-3);
	}

	.unk {
		background: var(--fill);
		border-radius: 14px;
		padding: 12px 14px;
	}
	.unk-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 10px;
		padding: 4px 0;
	}
	.unk-name {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-2);
	}
	.unk-guess {
		font-size: 13px;
		color: var(--blue);
		flex: none;
	}
	.unk-note {
		font-size: 12px;
		color: var(--text-4);
		margin-top: 6px;
	}

	.plan {
		background: var(--fill);
		border-radius: 14px;
		padding: 14px;
	}
	.chips {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-2);
		background: var(--surface);
		border: 1.5px solid var(--fill-strong);
		border-radius: 999px;
		padding: 7px 12px;
		transition: all 0.15s;
	}
	.chip.on {
		color: var(--blue);
		background: var(--blue-soft);
		border-color: var(--blue);
	}
	.period {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-2);
		margin-top: 10px;
	}
	.disclaim {
		font-size: 12px;
		color: var(--text-4);
		text-align: center;
		margin-top: 10px;
	}
</style>
