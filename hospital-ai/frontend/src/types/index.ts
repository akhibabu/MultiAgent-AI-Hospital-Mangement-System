export interface NavItem {
  label: string;
  path: string;
  icon?: string;
}

export interface PageMeta {
  title: string;
  description: string;
}

export type ThemeMode = 'light' | 'dark';
