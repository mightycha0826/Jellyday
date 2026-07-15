<script lang="ts">
	import { S, UI, medsOn, dayProgress, isTaken, toggleLog, installApp } from '$lib/state.svelte';
	import { SLOTS, todayKey, fmtHeader, dayName, greeting } from '$lib/utils';
	import Icon from '$lib/components/Icon.svelte';
	import MedRow from '$lib/components/MedRow.svelte';

	const today = todayKey();
	const meds = $derived(medsOn(today));
	const prog = $derived(dayProgress(today));
	const pct = $derived(prog.total ? Math.round((prog.done / prog.total) * 100) : 0);

	// 시간대별 그룹 (오늘 복용할 약이 있는 시간대만)
	const groups = $derived(
		SLOTS.map((s) => ({ slot: s, meds: meds.filter((m) => m.times.includes(s.id)) })).filter(
			(g) => g.meds.length > 0
		)
	);

	// 다음 복용: 아직 안 먹은 약이 남아 있는 가장 이른 시간대
	const next = $derived(
		groups.find((g) => g.meds.some((m) => !isTaken(m.id, today, g.slot.id)))
	);

	function openAdd() {
		UI.addChooserOpen = true;
	}
</script>

<div class="page">
	<header class="rise">
		<div>
			<p class="date">{fmtHeader(today)} {dayName(today)}</p>
			<h1>{greeting()}{S.profile?.nick ? `, ${S.profile.nick}님` : ''}</h1>
		</div>
		<div class="actions">
			{#if !S.installed}
				<button class="install" onclick={installApp}>앱 다운로드</button>
			{/if}
			<a href="/settings" class="gear" aria-label="설정">
				<svg viewBox="0 0 24 24" fill="currentColor"
					><path
						d="M13.6 2h-3.2a1 1 0 0 0-1 .82l-.34 1.98a7.6 7.6 0 0 0-1.6.93l-1.88-.76a1 1 0 0 0-1.24.45L2.74 8.18a1 1 0 0 0 .24 1.3l1.58 1.22a7.7 7.7 0 0 0 0 1.6l-1.58 1.22a1 1 0 0 0-.24 1.3l1.6 2.76a1 1 0 0 0 1.24.45l1.88-.76c.5.38 1.03.7 1.6.93l.34 1.98a1 1 0 0 0 1 .82h3.2a1 1 0 0 0 1-.82l.34-1.98c.57-.23 1.1-.55 1.6-.93l1.88.76a1 1 0 0 0 1.24-.45l1.6-2.76a1 1 0 0 0-.24-1.3l-1.58-1.22a7.7 7.7 0 0 0 0-1.6l1.58-1.22a1 1 0 0 0 .24-1.3l-1.6-2.76a1 1 0 0 0-1.24-.45l-1.88.76a7.6 7.6 0 0 0-1.6-.93l-.34-1.98a1 1 0 0 0-1-.82ZM12 15.4a3.4 3.4 0 1 1 0-6.8 3.4 3.4 0 0 1 0 6.8Z"
					/></svg
				>
			</a>
		</div>
	</header>

	{#if meds.length === 0}
		<!-- 빈 상태 -->
		<div class="card empty rise" style="animation-delay: 0.05s">
			<div class="pill-icon"><Icon name="pill" size={52} /></div>
			<h2>아직 등록된 약이 없어요</h2>
			<p>복용 중인 약을 추가하고<br />매일 복약 기록을 남겨보세요</p>
			<button class="btn" onclick={openAdd}>약 추가하기</button>
		</div>
	{:else}
		<!-- 오늘의 복약 진행 -->
		<section class="card prog rise" style="animation-delay: 0.05s">
			<p class="cap">오늘의 복약</p>
			<div class="prog-row">
				<strong>{prog.done}<span> / {prog.total}회 복용</span></strong>
				{#if prog.total > 0 && prog.done === prog.total}
					<span class="badge done">완료 🎉</span>
				{:else}
					<span class="badge">{pct}%</span>
				{/if}
			</div>
			<div class="bar" role="progressbar" aria-valuenow={pct} aria-valuemin="0" aria-valuemax="100">
				<div class="fill" style="width:{pct}%"></div>
			</div>
		</section>

		<!-- 다음 복용 -->
		{#if next}
			<section class="card next rise" style="animation-delay: 0.1s">
				<div class="next-emoji"><Icon name={next.slot.id} size={30} /></div>
				<div>
					<p class="cap">다음 복용 · {next.slot.label} {next.slot.time}</p>
					<p class="next-meds">
						{next.meds
							.filter((m) => !isTaken(m.id, today, next.slot.id))
							.map((m) => m.name)
							.join(', ')}
					</p>
				</div>
			</section>
		{/if}

		<!-- 시간대별 체크리스트 -->
		{#each groups as g, gi (g.slot.id)}
			<section class="group rise" style="animation-delay: {0.15 + gi * 0.05}s">
				<h3><Icon name={g.slot.id} size={20} /> {g.slot.label} <span>{g.slot.time}</span></h3>
				<div class="card list">
					{#each g.meds as m (m.id)}
						<MedRow
							color={m.color}
							name={m.name}
							sub={[m.dosage, m.memo].filter(Boolean).join(' · ')}
							taken={isTaken(m.id, today, g.slot.id)}
							onclick={() => toggleLog(m.id, today, g.slot.id)}
						/>
					{/each}
				</div>
			</section>
		{/each}

		<button
			class="btn ghost add rise"
			style="animation-delay: {0.2 + groups.length * 0.05}s"
			onclick={openAdd}
		>
			<svg viewBox="0 0 24 24" class="plus"><path d="M12 5v14M5 12h14" /></svg>
			약 추가하기
		</button>
	{/if}
</div>

<style>
	header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 12px;
		padding: 16px 0 20px;
	}
	header > div {
		min-width: 0; /* 닉네임이 길어도 버튼을 밀어내지 않고 줄바꿈 */
	}
	.date {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-3);
		margin-bottom: 2px;
	}
	h1 {
		font-size: 24px;
		font-weight: 700;
		letter-spacing: -0.02em;
	}
	.actions {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: none;
	}
	.install {
		height: 40px;
		padding: 0 16px;
		border-radius: 12px;
		background: var(--blue);
		color: #fff;
		font-size: 14px;
		font-weight: 700;
		transition:
			background 0.15s,
			transform 0.1s;
	}
	.install:active {
		background: var(--blue-press);
		transform: scale(0.97);
	}
	.gear {
		display: grid;
		place-items: center;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		color: var(--text-4);
		transition: background 0.15s;
	}
	.gear:active {
		background: var(--fill-strong);
	}
	.gear svg {
		width: 24px;
		height: 24px;
	}

	/* 빈 상태 */
	.empty {
		text-align: center;
		padding: 40px 24px 28px;
	}
	.pill-icon {
		font-size: 44px;
		margin-bottom: 12px;
	}
	.empty h2 {
		font-size: 18px;
		font-weight: 700;
		margin-bottom: 6px;
	}
	.empty p {
		color: var(--text-3);
		font-size: 14px;
		margin-bottom: 24px;
	}

	/* 진행 카드 */
	.cap {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-3);
	}
	.prog-row {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin: 6px 0 14px;
	}
	.prog strong {
		font-size: 28px;
		font-weight: 800;
		letter-spacing: -0.02em;
	}
	.prog strong span {
		font-size: 17px;
		font-weight: 600;
		color: var(--text-3);
	}
	.badge {
		font-size: 13px;
		font-weight: 700;
		color: var(--blue);
		background: var(--blue-soft);
		padding: 4px 10px;
		border-radius: 999px;
	}
	.badge.done {
		color: var(--green);
		background: var(--green-soft);
	}
	.bar {
		height: 8px;
		border-radius: 4px;
		background: var(--fill);
		overflow: hidden;
	}
	.fill {
		height: 100%;
		border-radius: 4px;
		background: var(--blue);
		transition: width 0.4s cubic-bezier(0.22, 1, 0.36, 1);
	}

	/* 다음 복용 */
	.next {
		display: flex;
		align-items: center;
		gap: 14px;
		margin-top: 12px;
		background: var(--blue-soft);
	}
	.next .cap {
		color: var(--blue);
	}
	.next-emoji {
		font-size: 28px;
	}
	.next-meds {
		font-size: 16px;
		font-weight: 700;
		margin-top: 2px;
	}

	/* 체크리스트 */
	.group {
		margin-top: 24px;
	}
	.group h3 {
		font-size: 15px;
		font-weight: 700;
		margin: 0 4px 8px;
	}
	.group h3 span {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-4);
		margin-left: 4px;
	}

	.add {
		margin-top: 24px;
	}
	.plus {
		width: 18px;
		height: 18px;
		fill: none;
		stroke: currentColor;
		stroke-width: 2.2;
		stroke-linecap: round;
	}
</style>
