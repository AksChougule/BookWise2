import { ReactNode } from "react";

type SectionContainerProps = {
  id: string;
  title: string;
  children: ReactNode;
};

export function SectionContainer({ id, title, children }: SectionContainerProps) {
  return (
    <section id={id} data-section-id={id} className="details-section">
      <h2>{title}</h2>
      <div>{children}</div>
    </section>
  );
}
