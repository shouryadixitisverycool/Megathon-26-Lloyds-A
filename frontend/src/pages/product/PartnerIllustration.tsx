import type { PartnerProduct } from "../../api/partners";

const LABELS: Record<PartnerProduct, string> = {
  EV_FINANCE: "electric car",
  SOLAR_FINANCE: "solar panels",
  GREEN_HOME: "a greener home",
};

/** Original local artwork: no image service, tracking pixel, or stock dependency. */
export function PartnerIllustration({ product, compact = false }: { product: PartnerProduct; compact?: boolean }) {
  return (
    <svg className={`partner-art${compact ? " is-compact" : ""}`} viewBox={compact ? "65 35 340 180" : "0 0 520 250"} role="img"
      aria-label={`Illustration of ${LABELS[product]}`}>
      <path className="partner-art-ground" d="M18 209c81-28 151-19 223-5 87 17 171 18 261-11v57H18z" />
      <circle className="partner-art-sun" cx="414" cy="54" r="27" />
      <path className="partner-art-orbit" d="M344 83c24-41 78-54 116-24" />
      <path className="partner-art-leaf" d="M78 155c6-28 27-43 58-45-5 30-22 49-52 54m22-22 30-22" />
      {product === "EV_FINANCE" && (
        <g className="partner-art-object">
          <path d="M129 152h231l-17-42c-5-12-15-19-29-19H196c-13 0-24 7-30 19z" />
          <path d="m183 111 12-20h105l15 20z" className="partner-art-window" />
          <path d="M119 151h252v34H119z" />
          <circle cx="174" cy="188" r="18" className="partner-art-wheel" />
          <circle cx="317" cy="188" r="18" className="partner-art-wheel" />
          <path d="M136 160h24m176 0h21" className="partner-art-detail" />
          <path d="m249 120-14 25h18l-8 18 29-32h-19l10-11z" className="partner-art-spark" />
        </g>
      )}
      {product === "SOLAR_FINANCE" && (
        <g className="partner-art-object">
          <path d="m136 135 111-74 116 74v74H136z" />
          <path d="m157 125 90-60 90 60" className="partner-art-detail" />
          <path d="M175 111h115l21 45H156z" className="partner-art-panel" />
          <path d="m203 112-11 43m43-43-1 43m30-43 9 43m-104-21h132" className="partner-art-panel-line" />
          <path d="M225 169h45v40h-45z" className="partner-art-window" />
          <path d="M247 169v40" className="partner-art-detail" />
        </g>
      )}
      {product === "GREEN_HOME" && (
        <g className="partner-art-object">
          <path d="m135 126 113-79 118 79v83H135z" />
          <path d="m156 119 92-64 96 64" className="partner-art-detail" />
          <path d="M174 128h51v40h-51zM278 128h49v40h-49z" className="partner-art-window" />
          <path d="M230 164c0-18 13-30 29-30s27 12 27 30v45h-56z" />
          <path d="M255 150v53m0-27c-10-2-17-8-19-17m19 28c9-1 16-7 20-15" className="partner-art-detail" />
          <path d="M117 209h272" className="partner-art-detail" />
        </g>
      )}
    </svg>
  );
}
