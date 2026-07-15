<script lang="ts">
	// 앱 전용 컬러 아이콘 세트 (이모지 대체)
	// pill=알약, morning=아침, noon=점심, evening=저녁, night=자기 전
	let { name, size = 20 }: { name: string; size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 48 48"
	fill="none"
	style="display:inline-block;vertical-align:middle;flex:none"
	aria-hidden="true"
>
	{#if name === 'pill'}
		<g transform="rotate(45 24 24)">
			<path d="M15 24 V14 a9 9 0 0 1 18 0 V24 Z" fill="#4EC3F7" />
			<path d="M15 24 V34 a9 9 0 0 0 18 0 V24 Z" fill="#DDE6EC" />
			<path d="M20.5 12.5 q3.5 -3 7 0" stroke="#fff" stroke-width="2.6" stroke-linecap="round" />
		</g>
	{:else if name === 'morning'}
		<path
			d="M24 2 28.8 9.3 36.9 6.2 36.5 14.9 44.9 17.2 39.5 24 44.9 30.8 36.5 33.1 36.9 41.8 28.8 38.7 24 46 19.2 38.7 11.1 41.8 11.5 33.1 3.1 30.8 8.5 24 3.1 17.2 11.5 14.9 11.1 6.2 19.2 9.3 Z"
			fill="#F6CB63"
			stroke="#F6CB63"
			stroke-width="2.4"
			stroke-linejoin="round"
		/>
		<circle cx="24" cy="24" r="12.5" fill="#FCDF7C" />
	{:else if name === 'noon'}
		<g stroke="#F4C05A" stroke-width="2.2" stroke-linecap="round">
			<line x1="34" y1="4" x2="34" y2="7.5" />
			<line x1="44.5" y1="15" x2="41.5" y2="16" />
			<line x1="42" y1="7.5" x2="39.7" y2="9.7" />
		</g>
		<circle cx="34" cy="15" r="7.5" fill="#F4C05A" />
		<g fill="#A9E1EF">
			<rect x="9" y="30" width="23" height="9" rx="4.5" />
			<circle cx="16" cy="30" r="6" />
			<circle cx="24" cy="27.5" r="8" />
			<circle cx="30" cy="31" r="5" />
		</g>
		<g fill="#7ECFE6">
			<rect x="24" y="34" width="16" height="7" rx="3.5" />
			<circle cx="29" cy="34" r="5" />
			<circle cx="35" cy="35" r="4" />
		</g>
	{:else if name === 'evening'}
		<path
			d="M28 6 A15 15 0 1 0 34 30 A11.5 11.5 0 1 1 28 6 Z"
			fill="#FBDE7E"
			transform="rotate(20 24 20)"
		/>
		<path
			d="M40 7 41 10.5 44.5 11.5 41 12.5 40 16 39 12.5 35.5 11.5 39 10.5 Z"
			fill="#FBDE7E"
		/>
		<path
			d="M43 21 43.7 23.3 46 24 43.7 24.7 43 27 42.3 24.7 40 24 42.3 23.3 Z"
			fill="#FBDE7E"
		/>
		<g fill="#FCF6E6">
			<rect x="10" y="34" width="20" height="8" rx="4" />
			<circle cx="16" cy="34" r="6" />
			<circle cx="23" cy="32.5" r="7" />
			<circle cx="28" cy="35" r="4.5" />
		</g>
	{:else if name === 'night'}
		<path
			d="M27 4 A16 16 0 1 0 34 30 A12 12 0 1 1 27 4 Z"
			fill="#FBD268"
			transform="rotate(15 22 18)"
		/>
		<g stroke="#8C8391" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none">
			<polyline points="27,13 31,13 27,17 31,17" />
			<polyline points="33,8 38,8 33,13 38,13" transform="scale(1.05)" />
			<polyline points="40,3 45,3 40,8 45,8" />
		</g>
		<g fill="#E9F5FB">
			<rect x="12" y="35" width="21" height="8" rx="4" />
			<circle cx="18" cy="35" r="6.5" />
			<circle cx="26" cy="33.5" r="7.5" />
			<circle cx="31" cy="36" r="5" />
		</g>
	{/if}
</svg>
