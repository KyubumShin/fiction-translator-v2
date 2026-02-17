import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import commonEn from "@/locales/en/common.json";
import settingsEn from "@/locales/en/settings.json";
import knowledgeEn from "@/locales/en/knowledge.json";
import projectsEn from "@/locales/en/projects.json";
import projectEn from "@/locales/en/project.json";
import editorEn from "@/locales/en/editor.json";
import pipelineEn from "@/locales/en/pipeline.json";

import commonKo from "@/locales/ko/common.json";
import settingsKo from "@/locales/ko/settings.json";
import knowledgeKo from "@/locales/ko/knowledge.json";
import projectsKo from "@/locales/ko/projects.json";
import projectKo from "@/locales/ko/project.json";
import editorKo from "@/locales/ko/editor.json";
import pipelineKo from "@/locales/ko/pipeline.json";

import commonJa from "@/locales/ja/common.json";
import settingsJa from "@/locales/ja/settings.json";
import knowledgeJa from "@/locales/ja/knowledge.json";
import projectsJa from "@/locales/ja/projects.json";
import projectJa from "@/locales/ja/project.json";
import editorJa from "@/locales/ja/editor.json";
import pipelineJa from "@/locales/ja/pipeline.json";

export const supportedLanguages = [
  { code: "en", name: "English", nativeName: "English" },
  { code: "ko", name: "Korean", nativeName: "한국어" },
  { code: "ja", name: "Japanese", nativeName: "日本語" },
] as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
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
      ko: {
        common: commonKo,
        settings: settingsKo,
        knowledge: knowledgeKo,
        projects: projectsKo,
        project: projectKo,
        editor: editorKo,
        pipeline: pipelineKo,
      },
      ja: {
        common: commonJa,
        settings: settingsJa,
        knowledge: knowledgeJa,
        projects: projectsJa,
        project: projectJa,
        editor: editorJa,
        pipeline: pipelineJa,
      },
    },
    fallbackLng: "en",
    defaultNS: "common",
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "fiction-translator-language",
    },
  });

export default i18n;
