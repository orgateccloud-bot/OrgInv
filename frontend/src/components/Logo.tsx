type Props = {
  size?: number;
  className?: string;
};

export function Logo({ size = 32, className }: Props) {
  return (
    <img
      src="/logo.png"
      width={size}
      height={size}
      className={className}
      alt="Orgatec"
      style={{ objectFit: "contain" }}
    />
  );
}
