import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
} from "../ui/select";
import {
  IMAGE_GENERATION_MODEL_DESCRIPTIONS,
  ImageGenerationModel,
} from "../../lib/models";

interface Props {
  imageGenerationModel: ImageGenerationModel;
  setImageGenerationModel: (imageGenerationModel: ImageGenerationModel) => void;
  shouldDisableUpdates?: boolean;
}

function ImageModelSettingsSection({
  imageGenerationModel,
  setImageGenerationModel,
  shouldDisableUpdates = false,
}: Props) {
  return (
    <div className="flex flex-col gap-y-2 justify-between text-sm">
      <div className="grid grid-cols-3 items-center gap-4">
        <span>Image Model:</span>
        <Select
          value={imageGenerationModel}
          onValueChange={(value: string) =>
            setImageGenerationModel(value as ImageGenerationModel)
          }
          disabled={shouldDisableUpdates}
        >
          <SelectTrigger className="col-span-2" id="image-model-settings">
            <span className="font-semibold">
              {IMAGE_GENERATION_MODEL_DESCRIPTIONS[imageGenerationModel].name}
            </span>
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              {Object.values(ImageGenerationModel).map((model) => (
                <SelectItem key={model} value={model}>
                  <div className="flex items-center">
                    <span className="font-semibold">
                      {IMAGE_GENERATION_MODEL_DESCRIPTIONS[model].name}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectGroup>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

export default ImageModelSettingsSection;
