import AudioLines from '@lucide/svelte/icons/audio-lines';
import Baby from '@lucide/svelte/icons/baby';
import Landmark from '@lucide/svelte/icons/landmark';
import ShoppingBasket from '@lucide/svelte/icons/shopping-basket';
import Tag from '@lucide/svelte/icons/tag';
import Trophy from '@lucide/svelte/icons/trophy';
import Utensils from '@lucide/svelte/icons/utensils';
import type { Category } from './event';

/** Le categorie si distinguono per icona, non per colore. */
export const CATEGORY_ICONS = {
	music: AudioLines,
	food: Utensils,
	sport: Trophy,
	culture: Landmark,
	kids: Baby,
	market: ShoppingBasket,
	other: Tag
} satisfies Record<Category, typeof Tag>;
