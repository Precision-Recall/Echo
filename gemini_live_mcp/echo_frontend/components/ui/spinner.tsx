import { cn } from "@/lib/utils";

export const Spinner = ({
  className,
  text,
  size = 24,
}: {
  className?: string;
  text?: string;
  size?: number;
}) => {
  const segments = 12;
  const segmentWidth = 2;

  return (
    <div className={cn("flex items-center gap-1", className)}>
      <svg
        className={`animate-spin`}
        viewBox="0 0 50 50"
        height={size}
        width={size}
      >
        {[...Array(segments)].map((_, index) => (
          <rect
            key={index}
            x="23.5"
            y="5"
            width={segmentWidth}
            height="10"
            rx="1"
            ry="1"
            fill="currentColor"
            transform={`rotate(${index * (360 / segments)} 25 25)`}
            opacity={1 - (index * 0.75) / segments}
          />
        ))}
      </svg>
      {text && <span className="text-inherit">{text}</span>}
    </div>
  );
};

