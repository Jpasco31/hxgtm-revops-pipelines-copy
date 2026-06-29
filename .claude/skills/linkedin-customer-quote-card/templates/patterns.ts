/**
 * Theme palettes aligned to Figma node 1480:22766 (Blue, Burgundy, Green).
 * Each entry maps the background, accent text color, and avatar tile base color.
 */

export type PatternType = 'blue' | 'burgundy' | 'green';

export interface ColorPalette {
  backgroundColor: string;
  accentColor: string;
  avatarBaseColor: string;
}

export const palettes: Record<PatternType, ColorPalette> = {
  blue: {
    backgroundColor: '#1D2733',
    accentColor: '#A6C4EE',
    avatarBaseColor: '#0F1924',
  },
  burgundy: {
    backgroundColor: '#400A20',
    accentColor: '#EE6C5B',
    avatarBaseColor: '#260814',
  },
  green: {
    backgroundColor: '#013F3C',
    accentColor: '#59BBB7',
    avatarBaseColor: '#002625',
  },
};

/**
 * Returns the palette for a given pattern type. Used by the card renderer.
 */
export function getPalette(patternType: PatternType): ColorPalette {
  return palettes[patternType];
}

/**
 * Export list in UI order.
 */
export const patternOrder: PatternType[] = ['blue', 'burgundy', 'green'];
