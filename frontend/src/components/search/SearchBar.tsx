import { Button } from "../ui/button";
import { Input } from "../ui/input";

type SearchBarProps = {
  value: string;
  loading: boolean;
  onChange: (value: string) => void;
  onSurprise: () => void;
};

export function SearchBar({ value, loading, onChange, onSurprise }: SearchBarProps) {
  return (
    <div className="search-controls">
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search by title, author, or keyword"
        aria-label="Search books"
      />
      <Button variant="secondary" onClick={onSurprise} disabled={loading}>
        Surprise Me
      </Button>
    </div>
  );
}
