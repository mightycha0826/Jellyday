<script lang="ts">
	import BottomSheet from './BottomSheet.svelte';
	import Icon from './Icon.svelte';
	import { UI, saveMed, deleteMed, toast } from '$lib/state.svelte';
	import { SLOTS, MED_COLORS, todayKey } from '$lib/utils';

	let name = $state('');
	let dosage = $state('');
	let times = $state<string[]>([]);
	let startDate = $state(todayKey());
	let endDate = $state('');
	let color = $state('blue');
	let memo = $state('');
	let saving = $state(false);

	// 시트가 열릴 때 편집 대상/프리셋으로 초기화
	$effect(() => {
		if (!UI.medFormOpen) return;
		const m = UI.editingMed;
		name = m?.name ?? UI.presetName;
		dosage = m?.dosage ?? '';
		times = m ? [...m.times] : ['morning'];
		startDate = m?.start_date ?? todayKey();
		endDate = m?.end_date ?? '';
		color = m?.color ?? 'blue';
		memo = m?.memo ?? '';
		UI.presetName = '';
	});

	function toggleSlot(id: string) {
		times = times.includes(id) ? times.filter((t) => t !== id) : [...times, id];
	}

	async function submit() {
		if (!name.trim() || times.length === 0 || saving) return;
		saving = true;
		const ok = await saveMed(
			{
				name: name.trim(),
				dosage: dosage.trim(),
				times,
				start_date: startDate,
				end_date: endDate || null,
				color,
				memo: memo.trim()
			},
			UI.editingMed?.id
		);
		saving = false;
		if (ok) {
			toast(UI.editingMed ? '약 정보를 수정했어요' : '약을 추가했어요');
			UI.medFormOpen = false;
			UI.editingMed = null;
		}
	}

	async function remove() {
		if (!UI.editingMed) return;
		await deleteMed(UI.editingMed.id);
		toast('약을 삭제했어요');
		UI.medFormOpen = false;
		UI.editingMed = null;
	}
</script>

<BottomSheet bind:open={UI.medFormOpen} title={UI.editingMed ? '약 정보 수정' : '약 추가하기'}>
	<div class="form">
		<label class="lbl" for="med-name">이름</label>
		<input id="med-name" class="field" placeholder="예) 타이레놀" bind:value={name} />

		<label class="lbl" for="med-dose">용량 <em>(선택)</em></label>
		<input id="med-dose" class="field" placeholder="예) 500mg 1정" bind:value={dosage} />

		<span class="lbl">복용 시간대</span>
		<div class="slots">
			{#each SLOTS as s (s.id)}
				<button
					type="button"
					class="slot"
					class:on={times.includes(s.id)}
					onclick={() => toggleSlot(s.id)}
				>
					<Icon name={s.id} size={22} />{s.label}
				</button>
			{/each}
		</div>

		<div class="row2">
			<div>
				<label class="lbl" for="med-start">시작일</label>
				<input id="med-start" class="field" type="date" bind:value={startDate} />
			</div>
			<div>
				<label class="lbl" for="med-end">종료일 <em>(선택)</em></label>
				<input id="med-end" class="field" type="date" bind:value={endDate} min={startDate} />
			</div>
		</div>

		<span class="lbl">색상</span>
		<div class="colors" role="radiogroup" aria-label="색상 선택">
			{#each MED_COLORS as c (c.id)}
				<button
					type="button"
					role="radio"
					aria-checked={color === c.id}
					aria-label={c.id}
					class="dot"
					class:on={color === c.id}
					style="background:{c.bg}; --fg:{c.fg}"
					onclick={() => (color = c.id)}
				>
					<span style="background:{c.fg}"></span>
				</button>
			{/each}
		</div>

		<label class="lbl" for="med-memo">메모 <em>(선택)</em></label>
		<input id="med-memo" class="field" placeholder="예) 식후 30분" bind:value={memo} />

		<button class="btn" style="margin-top: 20px" disabled={!name.trim() || times.length === 0 || saving} onclick={submit}>
			{UI.editingMed ? '수정 완료' : '추가하기'}
		</button>
		{#if UI.editingMed}
			<button class="del" onclick={remove}>이 약 삭제하기</button>
		{/if}
	</div>
</BottomSheet>

<style>
	.form {
		display: flex;
		flex-direction: column;
	}
	.lbl {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-3);
		margin: 14px 0 6px;
	}
	.lbl:first-child {
		margin-top: 0;
	}
	.lbl em {
		font-style: normal;
		font-weight: 400;
		color: var(--text-4);
	}
	.slots {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 8px;
	}
	.slot {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		padding: 10px 0 8px;
		border-radius: var(--r-chip);
		background: var(--fill);
		color: var(--text-2);
		font-size: 13px;
		font-weight: 600;
		border: 1.5px solid transparent;
		transition: all 0.15s;
	}
	.slot.on {
		background: var(--blue-soft);
		color: var(--blue);
		border-color: var(--blue);
	}
	.row2 {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	.row2 > div {
		min-width: 0; /* 날짜 입력칸이 칸을 넘치지 않게 */
	}
	.colors {
		display: flex;
		gap: 10px;
	}
	.dot {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		border: 2px solid transparent;
		transition: border-color 0.15s;
	}
	.dot.on {
		border-color: var(--fg);
	}
	.dot span {
		width: 16px;
		height: 16px;
		border-radius: 50%;
	}
	.del {
		margin-top: 12px;
		height: 44px;
		color: var(--red);
		font-size: 14px;
		font-weight: 600;
	}
</style>
