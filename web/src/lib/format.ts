/** Numeri all'italiana: 1.234 (anche da quattro cifre, dove it-IT di default non mette il punto). */
const nf = new Intl.NumberFormat('it-IT', { useGrouping: 'always' });
export const fmtNum = (n: number): string => nf.format(n);
