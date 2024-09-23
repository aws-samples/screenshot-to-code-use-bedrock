// Keep in sync with backend (llm.py)
// Order here matches dropdown order
export enum CodeGenerationModel {
  CLAUDE_3_5_SONNET_2024_06_20 = "anthropic.claude-3-5-sonnet-20240620-v1:0",
  CLAUDE_3_OPUS_2024_02_29 = "anthropic.claude-3-opus-20240229-v1:0",
  CLAUDE_3_SONNET_2024_02_29 = "anthropic.claude-3-sonnet-20240229-v1:0",
  CLAUDE_3_HAIKU_2024_03_07 = "anthropic.claude-3-haiku-20240307-v1:0",
}

// Will generate a static error if a model in the enum above is not in the descriptions
export const CODE_GENERATION_MODEL_DESCRIPTIONS: {
  [key in CodeGenerationModel]: { name: string; inBeta: boolean };
} = {
  "anthropic.claude-3-5-sonnet-20240620-v1:0": { name: "Claude 3.5 Sonnet", inBeta: false },
  "anthropic.claude-3-opus-20240229-v1:0": { name: "Claude 3 Opus", inBeta: false },
  "anthropic.claude-3-sonnet-20240229-v1:0": { name: "Claude 3 Sonnet", inBeta: false },
  "anthropic.claude-3-haiku-20240307-v1:0": { name: "Claude 3 Haiku", inBeta: false },
};
