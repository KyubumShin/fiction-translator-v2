import "@testing-library/jest-dom/vitest";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import commonEn from "../locales/en/common.json";
import settingsEn from "../locales/en/settings.json";
import knowledgeEn from "../locales/en/knowledge.json";
import projectsEn from "../locales/en/projects.json";
import projectEn from "../locales/en/project.json";
import editorEn from "../locales/en/editor.json";
import pipelineEn from "../locales/en/pipeline.json";

i18n.use(initReactI18next).init({
  lng: "en",
  resources: {
    en: {
      common: commonEn,
      settings: settingsEn,
      knowledge: knowledgeEn,
      projects: projectsEn,
      project: projectEn,
      editor: editorEn,
      pipeline: pipelineEn,
    },
  },
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: {
    escapeValue: false,
  },
});
