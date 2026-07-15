<script lang="ts">
	// "약 추가하기" → 직접 입력 / 약봉투 촬영 선택 시트
	import { goto } from '$app/navigation';
	import BottomSheet from './BottomSheet.svelte';
	import { UI } from '$lib/state.svelte';

	function manual() {
		UI.addChooserOpen = false;
		UI.editingMed = null;
		UI.medFormOpen = true;
	}
	function shoot() {
		UI.addChooserOpen = false;
		void goto('/camera');
	}
</script>

<BottomSheet bind:open={UI.addChooserOpen} title="약 추가하기">
	<div class="opts">
		<button class="opt" onclick={manual}>
			<span class="ic" aria-hidden="true">
				<svg viewBox="0 0 48 48" fill="none">
					<path
						d="M11 5 h18 l7 7 v29 a2.5 2.5 0 0 1-2.5 2.5 H11 A2.5 2.5 0 0 1 8.5 40 V7.5 A2.5 2.5 0 0 1 11 5 Z"
						fill="#E9ECEF"
						stroke="#14181f"
						stroke-width="2.4"
						stroke-linejoin="round"
					/>
					<path
						d="M29 5 v4.5 a2.5 2.5 0 0 0 2.5 2.5 H36 Z"
						fill="#AEB6BF"
						stroke="#14181f"
						stroke-width="2.4"
						stroke-linejoin="round"
					/>
					<g stroke="#14181f" stroke-width="2.4" stroke-linecap="round">
						<line x1="14" y1="13" x2="28" y2="13" />
						<line x1="14" y1="18.5" x2="30" y2="18.5" />
						<line x1="14" y1="24" x2="27" y2="24" />
						<line x1="14" y1="29.5" x2="24" y2="29.5" />
						<line x1="14" y1="35" x2="22" y2="35" />
					</g>
					<g transform="translate(33.5 29) rotate(45)">
						<rect
							x="-4"
							y="-13"
							width="8"
							height="4.5"
							rx="1.2"
							fill="#B5835A"
							stroke="#14181f"
							stroke-width="2"
							stroke-linejoin="round"
						/>
						<rect
							x="-4"
							y="-8.5"
							width="8"
							height="17"
							fill="#FCD85D"
							stroke="#14181f"
							stroke-width="2"
							stroke-linejoin="round"
						/>
						<path
							d="M-4 8.5 H4 L0 16 Z"
							fill="#FCD85D"
							stroke="#14181f"
							stroke-width="2"
							stroke-linejoin="round"
						/>
						<path d="M-1.6 13 H1.6 L0 16 Z" fill="#5b6472" />
					</g>
				</svg>
			</span>
			<span class="tx">
				<span class="t">직접 추가하기</span>
				<span class="s">약 이름과 복용 시간을 직접 입력해요</span>
			</span>
			<svg class="chev" viewBox="0 0 24 24"><path d="m9.5 6 5.5 6-5.5 6" /></svg>
		</button>

		<button class="opt" onclick={shoot}>
			<span class="ic" aria-hidden="true">
				<svg viewBox="0 0 48 48" fill="none">
					<path
						d="M18 15 L20.5 10 A1.5 1.5 0 0 1 21.8 9.2 H26.2 A1.5 1.5 0 0 1 27.5 10 L30 15 Z"
						fill="#9AA4AF"
					/>
					<rect x="4" y="14" width="40" height="26" rx="4.5" fill="#8C97A4" />
					<rect x="9" y="18.5" width="6.5" height="3" rx="1.5" fill="#E4E8EC" />
					<circle cx="24" cy="28" r="10" fill="#F5CE1E" />
					<circle cx="24" cy="28" r="6.5" fill="#F1F5F8" />
					<path
						d="M20 24.5 a6 6 0 0 1 5.5 -1.8"
						stroke="#ffffff"
						stroke-width="2"
						stroke-linecap="round"
						fill="none"
					/>
				</svg>
			</span>
			<span class="tx">
				<span class="t">촬영하기</span>
				<span class="s">약봉투를 찍어 자동으로 인식해요</span>
			</span>
			<svg class="chev" viewBox="0 0 24 24"><path d="m9.5 6 5.5 6-5.5 6" /></svg>
		</button>
	</div>
</BottomSheet>

<style>
	.opts {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding-bottom: 6px;
	}
	.opt {
		display: flex;
		align-items: center;
		gap: 14px;
		width: 100%;
		padding: 16px;
		border-radius: 16px;
		background: var(--fill);
		text-align: left;
		transition:
			background 0.15s,
			transform 0.1s;
	}
	.opt:active {
		background: var(--fill-strong);
		transform: scale(0.99);
	}
	.ic {
		flex: none;
		width: 46px;
		height: 46px;
		border-radius: 14px;
		background: var(--surface);
		display: grid;
		place-items: center;
	}
	.ic svg {
		width: 30px;
		height: 30px;
	}
	.tx {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.t {
		font-size: 16px;
		font-weight: 700;
	}
	.s {
		font-size: 13px;
		color: var(--text-3);
	}
	.chev {
		flex: none;
		width: 20px;
		height: 20px;
		fill: none;
		stroke: var(--text-4);
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
</style>
