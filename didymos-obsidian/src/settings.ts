export interface DidymosSettings {
  apiEndpoint: string;
  userToken: string;
  vaultId: string;
  autoSync: boolean;
  syncMode: "manual" | "hourly" | "realtime";
  realtimeCooldownMinutes: number;
  premiumRealtime: boolean;
  language: "en" | "ko";
  usageBudgetPerDay: number;
  usageUsedToday: number;
  usageResetAt: string;
  privacyMode: "full" | "summary" | "metadata";
  excludedFolders: string[];
  exportFolder: string;
  localMode: boolean;
  localOpenAIApiKey: string;
  autoExportOntology: boolean;
  bulkProcessOnStart: boolean;
  appendOntologyToNote: boolean;
  ontologyFormat: "json";
  decisionFolder: string;
}

export const DEFAULT_SETTINGS: DidymosSettings = {
  apiEndpoint: "http://localhost:8000/api/v1",
  userToken: "",
  vaultId: "",
  autoSync: true,
  syncMode: "manual",
  realtimeCooldownMinutes: 10,
  premiumRealtime: false,
  language: "ko",
  usageBudgetPerDay: 100,
  usageUsedToday: 0,
  usageResetAt: "",
  privacyMode: "full",
  excludedFolders: [],
  exportFolder: "Didymos/Ontology",
  localMode: false,
  localOpenAIApiKey: "",
  autoExportOntology: false,
  bulkProcessOnStart: false,
  appendOntologyToNote: false,
  ontologyFormat: "json",
  decisionFolder: "Didymos/Decisions",
};
