const SectionCard = ({ title, children, className = '' }) => (
  <div className={`card ${className}`}>
    <h2 className="text-utility font-sf-display text-apple-ink mb-6">{title}</h2>
    <div className="space-y-5">{children}</div>
  </div>
)

export default SectionCard
