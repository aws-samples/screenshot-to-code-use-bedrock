// Keep in sync with backend (llm.py)
// Order here matches dropdown order
export enum CodeGenerationModel {
  CLAUDE_3_5_SONNET_2024_10_22 = "anthropic.claude-3-5-sonnet-20241022-v2:0",
  CLAUDE_3_5_SONNET_2024_06_20 = "anthropic.claude-3-5-sonnet-20240620-v1:0",
  CLAUDE_3_OPUS_2024_02_29 = "anthropic.claude-3-opus-20240229-v1:0",
  CLAUDE_3_SONNET_2024_02_29 = "anthropic.claude-3-sonnet-20240229-v1:0",
  CLAUDE_3_HAIKU_2024_03_07 = "anthropic.claude-3-haiku-20240307-v1:0",
  NOVA_LITE = "amazon.nova-lite-v1:0",
  NOVA_PRO = "amazon.nova-pro-v1:0",
}

export enum ImageGenerationModel {
  NOVA_CANVAS = "amazon.nova-canvas-v1:0",
  TITAN_V1 = "amazon.titan-image-generator-v1:0",
  TITAN_V2 = "amazon.titan-image-generator-v2:0",
}

// Will generate a static error if a model in the enum above is not in the descriptions
export const CODE_GENERATION_MODEL_DESCRIPTIONS: {
  [key in CodeGenerationModel]: { name: string; inBeta: boolean };
} = {
  "anthropic.claude-3-5-sonnet-20241022-v2:0": { name: "Claude 3.5 Sonnet v2", inBeta: false },
  "anthropic.claude-3-5-sonnet-20240620-v1:0": { name: "Claude 3.5 Sonnet", inBeta: false },
  "anthropic.claude-3-opus-20240229-v1:0": { name: "Claude 3 Opus", inBeta: false },
  "anthropic.claude-3-sonnet-20240229-v1:0": { name: "Claude 3 Sonnet", inBeta: false },
  "anthropic.claude-3-haiku-20240307-v1:0": { name: "Claude 3 Haiku", inBeta: false },
  "amazon.nova-lite-v1:0": { name: "Nova Lite", inBeta: false },
  "amazon.nova-pro-v1:0": { name: "Nova Pro", inBeta: false },
};

export const IMAGE_GENERATION_MODEL_DESCRIPTIONS: {
  [key in ImageGenerationModel]: { name: string; inBeta: boolean };
} = {
  "amazon.nova-canvas-v1:0": { name: "Nova Canvas", inBeta: false },
  "amazon.titan-image-generator-v1:0": { name: "Titan v1", inBeta: false },
  "amazon.titan-image-generator-v2:0": { name: "Titan v2", inBeta: false },
};
