import { useEffect, useState } from "react";

interface Props {
  onFinished: () => void;
}

const WORDS = ["Parse", "Embed", "Retrieve", "Synthesize"];

export function PreLoader({ onFinished }: Props) {
  const [progress, setProgress] = useState(0);
  const [wordIndex, setWordIndex] = useState(0);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    const startTime = performance.now();
    const duration = 2400; // ~2.4 seconds loading duration

    let animationFrameId: number;

    const update = (time: number) => {
      const elapsed = time - startTime;
      const pct = Math.min(elapsed / duration, 1);
      const currentProgress = Math.floor(pct * 100);
      setProgress(currentProgress);

      // Map progress percentage to current word index
      const wordStep = Math.floor(pct * WORDS.length);
      setWordIndex(Math.min(wordStep, WORDS.length - 1));

      if (pct < 1) {
        animationFrameId = requestAnimationFrame(update);
      } else {
        // Start fading out when 100 is reached
        setIsFadingOut(true);
        const timer = setTimeout(() => {
          onFinished();
        }, 800); // must match transition duration in CSS
        return () => clearTimeout(timer);
      }
    };

    animationFrameId = requestAnimationFrame(update);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [onFinished]);

  const padNumber = (num: number) => {
    return String(num).padStart(3, "0");
  };

  return (
    <div className={`pre-loader ${isFadingOut ? "pre-loader--fade-out" : ""}`}>
      <div className="pre-loader-top">
        <span className="pre-loader-tag">DOCUMENT AI</span>
      </div>

      <div className="pre-loader-center">
        <div className="pre-loader-word-container">
          <span className="pre-loader-word">{WORDS[wordIndex]}</span>
        </div>
      </div>

      <div className="pre-loader-bottom">
        <div className="pre-loader-counter">{padNumber(progress)}</div>
      </div>

      <div className="pre-loader-bar-container">
        <div
          className="pre-loader-bar-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
