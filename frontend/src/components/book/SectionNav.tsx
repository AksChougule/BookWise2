type NavItem = {
  id: string;
  label: string;
};

type SectionNavProps = {
  items: NavItem[];
  activeId: string;
  onNavigate: (id: string) => void;
};

export function SectionNav({ items, activeId, onNavigate }: SectionNavProps) {
  return (
    <nav className="section-nav" aria-label="Book sections">
      {items.map((item) => (
        <button
          key={item.id}
          className={activeId === item.id ? "active" : ""}
          onClick={() => onNavigate(item.id)}
          type="button"
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
