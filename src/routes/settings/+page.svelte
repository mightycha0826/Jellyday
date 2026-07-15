<script lang="ts">
	import { goto } from '$app/navigation';
	import { S, UI, updateNick, toast, type Medication } from '$lib/state.svelte';
	import { slotLabel } from '$lib/utils';
	import MedRow from '$lib/components/MedRow.svelte';

	let editingNick = $state(false);
	let nickDraft = $state('');

	function startNick() {
		nickDraft = S.profile?.nick ?? '';
		editingNick = true;
	}
	async function saveNick() {
		const v = nickDraft.trim();
		if (v && v !== S.profile?.nick) {
			await updateNick(v);
			toast('닉네임을 변경했어요');
		}
		editingNick = false;
	}

	function editMed(m: Medication) {
		UI.editingMed = m;
		UI.medFormOpen = true;
	}
	function addMed() {
		UI.addChooserOpen = true;
	}
</script>

<div class="page">
	<header class="rise">
		<button class="back" onclick={() => goto('/')} aria-label="뒤로가기">
			<svg viewBox="0 0 24 24"><path d="M15 5.5 8.5 12l6.5 6.5" /></svg>
		</button>
		<h1>설정</h1>
	</header>

	<h3 class="sec rise" style="animation-delay: 0.05s">프로필</h3>
	<section class="card list rise" style="animation-delay: 0.05s">
		{#if editingNick}
			<div class="nick-edit">
				<input
					class="field"
					bind:value={nickDraft}
					maxlength="12"
					placeholder="닉네임"
					onkeydown={(e) => e.key === 'Enter' && saveNick()}
				/>
				<button class="btn save" onclick={saveNick}>저장</button>
			</div>
		{:else}
			<button class="cell" onclick={startNick}>
				<span class="ci">
					<span class="cl">닉네임</span>
					<span class="cv">{S.profile?.nick ?? '-'}</span>
				</span>
				<svg class="chev" viewBox="0 0 24 24"><path d="m9.5 6 5.5 6-5.5 6" /></svg>
			</button>
		{/if}
	</section>

	<div class="sec-row rise" style="animation-delay: 0.1s">
		<h3 class="sec">내 약 관리</h3>
		<button class="mini" onclick={addMed}>+ 추가</button>
	</div>
	<section class="card list rise" style="animation-delay: 0.1s">
		{#if S.meds.length === 0}
			<p class="none">등록된 약이 없어요</p>
		{:else}
			{#each S.meds as m (m.id)}
				<MedRow
					color={m.color}
					name={m.name}
					sub={`${m.times.map(slotLabel).join(' · ')}${m.dosage ? ` · ${m.dosage}` : ''}`}
					trailing="chevron"
					onclick={() => editMed(m)}
				/>
			{/each}
		{/if}
	</section>

</div>

<style>
	header {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 12px 0 20px;
	}
	.back {
		width: 40px;
		height: 40px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		color: var(--text-2);
		margin-left: -8px;
	}
	.back:active {
		background: var(--fill-strong);
	}
	.back svg,
	.chev {
		width: 22px;
		height: 22px;
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	h1 {
		font-size: 22px;
		font-weight: 700;
	}

	.sec {
		font-size: 14px;
		font-weight: 700;
		color: var(--text-3);
		margin: 0 4px 8px;
	}
	.sec-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 24px;
	}
	.sec-row .sec {
		margin-bottom: 8px;
	}
	.mini {
		font-size: 13px;
		font-weight: 700;
		color: var(--blue);
		padding: 4px 10px;
		border-radius: 8px;
	}
	.mini:active {
		background: var(--blue-soft);
	}

	.cell {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 14px 12px;
		border-radius: 14px;
		text-align: left;
		transition: background 0.15s;
	}
	.cell:active {
		background: var(--fill);
	}
	.ci {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.cl {
		font-size: 13px;
		color: var(--text-3);
	}
	.cv {
		font-size: 16px;
		font-weight: 600;
	}
	.chev {
		color: var(--text-4);
		flex: none;
	}
	.none {
		color: var(--text-3);
		font-size: 14px;
		text-align: center;
		padding: 22px 0;
	}
	.nick-edit {
		display: flex;
		gap: 8px;
		padding: 8px 4px;
	}
	.save {
		width: 76px;
		flex: none;
	}
</style>
