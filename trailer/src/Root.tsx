import "./index.css";
import { Composition } from "remotion";
import { MartelCodeTrailer } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MartelCodeTrailer"
        component={MartelCodeTrailer}
        durationInFrames={360}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
