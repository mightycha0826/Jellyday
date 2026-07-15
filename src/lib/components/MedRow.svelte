<script lang="ts">
	// 약 리스트 행 — 홈·캘린더(체크 토글)·설정(수정 이동) 공용
	import Icon from './Icon.svelte';
	import { medColor } from '$lib/utils';

	let {
		color = 'blue',
		name,
		sub = '',
		trailing = 'check',
		taken = false,
		disabled = false,
		onclick
	}: {
		color?: string;
		name: string;
		sub?: string;
		trailing?: 'check' | 'chevron';
		taken?: boolean;
		disabled?: boolean;
		onclick?: () => void;
	} = $props();
</script>

<button
	class="row"
	class:taken
	{disabled}
	{onclick}
	aria-pressed={trailing === 'check' ? taken : undefined}
>
	<span class="chip" style="background:{medColor(color).bg}"><Icon name="pill" size={24} /></span>
	<span class="info">
		<span class="name">{name}</span>
		{#if sub}<span class="sub">{sub}</span>{/if}
	</span>
	{#if trailing === 'check'}
		<span class="check" aria-hidden="true">
			<svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
		</span>
	{:else}
		<svg class="chev" viewBox="0 0 24 24"><path d="m9.5 6 5.5 6-5.5 6" /></svg>
	{/if}
</button>

<style>
	.row {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 12px;
		border-radius: 14px;
		text-align: left;
		transition: background 0.15s;
	}
	.row:active:not(:disabled) {
		background: var(--fill);
	}
	.row:disabled {
		opacity: 0.55;
		cursor: default;
	}
	.chip {
		flex: none;
		width: 42px;
		height: 42px;
		border-radius: 13px;
		display: grid;
		place-items: center;
	}
	.info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.name {
		font-size: 16px;
		font-weight: 600;
		transition: color 0.15s;
	}
	.sub {
		font-size: 13px;
		color: var(--text-3);
	}
	.check {
		flex: none;
		width: 26px;
		height: 26px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		background: var(--fill-strong);
		color: #fff;
		transition: background 0.15s;
	}
	.check svg {
		width: 15px;
		height: 15px;
		fill: none;
		stroke: currentColor;
		stroke-width: 2.6;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.row.taken .check {
		background: var(--blue);
	}
	.row.taken .name {
		color: var(--text-4);
		text-decoration: line-through;
	}
	.chev {
		flex: none;
		width: 22px;
		height: 22px;
		fill: none;
		stroke: var(--text-4);
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
</style>
