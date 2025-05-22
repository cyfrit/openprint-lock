export interface SettingsState {
  baseUrl: string;
  token: string;
  isDarkMode: boolean;
  setBaseUrl: (url: string) => void;
  setToken: (token: string) => void;
  toggleDarkMode: () => void;
  reset: () => void;
}
