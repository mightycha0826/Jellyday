<script lang="ts">
	import { medsOn, dayProgress, isTaken, toggleLog, loadMonth } from '$lib/state.svelte';
	import { SLOTS, todayKey, fmtHeader, dayName, dateKey, slotLabel } from '$lib/utils';
	import MedRow from '$lib/components/MedRow.svelte';

	const today = todayKey();
	let selected = $state(todayKey());
	let viewY = $state(new Date().getFullYear());
	let viewM = $state(new Date().getMonth()); // 0-based

	// 보는 달의 로그 로드
	$effect(() => {
		const ym = `${viewY}-${String(viewM + 1).padStart(2, '0')}`;
		void loadMonth(ym);
	});

	const WEEK = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

	// 달력 셀: 앞쪽 빈칸 + 날짜들
	const cells = $derived.by(() => {
		const first = new Date(viewY, viewM, 1);
		const last = new Date(viewY, viewM + 1, 0);
		const out: (string | null)[] = Array(first.getDay()).fill(null);
		for (let d = 1; d <= last.getDate(); d++) out.push(dateKey(new Date(viewY, viewM, d)));
		return out;
	});

	function move(dir: number) {
		const d = new Date(viewY, viewM + dir, 1);
		viewY = d.getFullYear();
		viewM = d.getMonth();
	}

	function select(key: string) {
		selected = key;
	}

	// 선택 날짜의 복용 항목 (시간대 순)
	const items = $derived.by(() => {
		const out: { med: ReturnType<typeof medsOn>[number]; slot: string }[] = [];
		for (const s of SLOTS)
			for (const m of medsOn(selected)) if (m.times.includes(s.id)) out.push({ med: m, slot: s.id });
		return out;
	});

	const selProg = $derived(dayProgress(selected));

	/** 날짜 셀 상태: 'full' | 'part' | 'none' | '' */
	function dayState(key: string): string {
		if (key > today) return '';
		const p = dayProgress(key);
		if (p.total === 0) return '';
		if (p.done === p.total) return 'full';
		if (p.done > 0) return 'part';
		return 'none';
	}
</script>

<div class="page">
	<header class="rise">
		<div>
			<h1>{fmtHeader(selected)}</h1>
			<p class="day">{dayName(selected)}</p>
		</div>
		{#if selProg.total > 0}
			<div class="sum" class:ok={selProg.done === selProg.total}>
				{selProg.done}/{selProg.total}
			</div>
		{/if}
	</header>

	<section class="card cal rise" style="animation-delay: 0.05s">
		<div class="nav">
			<button onclick={() => move(-1)} aria-label="이전 달">
				<svg viewBox="0 0 24 24"><path d="M14.5 6 9 12l5.5 6" /></svg>
			</button>
			<strong>{viewY}년 {viewM + 1}월</strong>
			<button onclick={() => move(1)} aria-label="다음 달">
				<svg viewBox="0 0 24 24"><path d="m9.5 6 5.5 6-5.5 6" /></svg>
			</button>
		</div>
		<div class="week" aria-hidden="true">
			{#each WEEK as w, i (i)}
				<span class:sun={i === 0} class:sat={i === 6}>{w}</span>
			{/each}
		</div>
		<div class="grid">
			{#each cells as c, i (i)}
				{#if c === null}
					<span></span>
				{:else}
					{@const st = dayState(c)}
					<button
						class="cell"
						class:sel={c === selected}
						class:today={c === today}
						onclick={() => select(c)}
					>
						{Number(c.slice(8))}
						<i class="dot {st}" aria-hidden="true"></i>
					</button>
				{/if}
			{/each}
		</div>
	</section>

	<section class="rise" style="animation-delay: 0.1s; margin-top: 24px">
		<h3 class="sec">복약 기록</h3>
		{#if items.length === 0}
			<div class="card none">이 날짜에 복용할 약이 없어요</div>
		{:else}
			<div class="card list">
				{#each items as it (it.med.id + it.slot)}
					<MedRow
						color={it.med.color}
						name={it.med.name}
						sub={`${slotLabel(it.slot)}${it.med.dosage ? ` · ${it.med.dosage}` : ''}`}
						taken={isTaken(it.med.id, selected, it.slot)}
						disabled={selected > today}
						onclick={() => toggleLog(it.med.id, selected, it.slot)}
					/>
				{/each}
			</div>
		{/if}
	</section>
</div>

<style>
	header {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		padding: 16px 4px 20px;
	}
	h1 {
		font-size: 30px;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.15;
	}
	.day {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-3);
	}
	.sum {
		font-size: 15px;
		font-weight: 700;
		color: var(--text-3);
		background: var(--surface);
		border-radius: 12px;
		padding: 8px 14px;
	}
	.sum.ok {
		color: var(--blue);
		background: var(--blue-soft);
	}

	/* 달력 */
	.cal {
		padding: 16px;
	}
	.nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 10px;
	}
	.nav strong {
		font-size: 16px;
		font-weight: 700;
	}
	.nav button {
		width: 36px;
		height: 36px;
		border-radius: 10px;
		display: grid;
		place-items: center;
		color: var(--text-3);
	}
	.nav button:active {
		background: var(--fill);
	}
	.nav svg {
		width: 20px;
		height: 20px;
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.week {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		margin-bottom: 4px;
	}
	.week span {
		text-align: center;
		font-size: 12px;
		font-weight: 700;
		color: var(--text-4);
		padding: 6px 0;
	}
	.week .sun {
		color: var(--red);
	}
	.week .sat {
		color: var(--blue);
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		row-gap: 2px;
	}
	.cell {
		position: relative;
		aspect-ratio: 1 / 1.05;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 3px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-2);
		border-radius: 12px;
		transition: background 0.15s;
	}
	.cell.today {
		color: var(--blue);
		font-weight: 800;
	}
	.cell.sel {
		background: var(--text);
		color: #fff;
	}
	.dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: transparent;
	}
	.dot.full {
		background: var(--blue);
	}
	.dot.part {
		background: var(--text-4);
	}
	.dot.none {
		background: var(--fill-strong);
	}
	.cell.sel .dot.full {
		background: #fff;
	}

	/* 기록 리스트 */
	.sec {
		font-size: 15px;
		font-weight: 700;
		margin: 0 4px 8px;
	}
	.none {
		color: var(--text-3);
		font-size: 14px;
		text-align: center;
		padding: 28px 20px;
	}
</style>
