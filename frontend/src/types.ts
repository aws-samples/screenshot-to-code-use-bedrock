import { Stack } from "./lib/stacks";
import { CodeGenerationModel, ImageGenerationModel } from "./lib/models";

export enum EditorTheme {
  ESPRESSO = "espresso",
  COBALT = "cobalt",
}

export interface Settings {
  screenshotOneApiKey: string | null;
  isImageGenerationEnabled: boolean;
  imageGenerationModel: ImageGenerationModel;
  editorTheme: EditorTheme;
  generatedCodeConfig: Stack;
  codeGenerationModel: CodeGenerationModel;
  // Only relevant for hosted version
  isTermOfServiceAccepted: boolean;
  bedrockAccessKey: string | null;
  bedrockSecretKey: string | null;
  bedrockRegion: string | null;
}

export enum AppState {
  INITIAL = "INITIAL",
  CODING = "CODING",
  CODE_READY = "CODE_READY",
}

export enum ScreenRecorderState {
  INITIAL = "initial",
  RECORDING = "recording",
  FINISHED = "finished",
}

export interface CodeGenerationParams {
  generationType: "create" | "update";
  inputMode: "image" | "video";
  image: string;
  resultImage?: string;
  history?: string[];
  isImportedFromCode?: boolean;
}

export type FullGenerationSettings = CodeGenerationParams & Settings;
