import { Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { languages } from '../../../../shared/brand';
import { setAppLanguage, type SupportedLanguage } from '../i18n';

export function LanguageSwitcher({ className = '', compact = false }: { className?: string; compact?: boolean }) {
  const { i18n } = useTranslation();
  return <label className={`app-button console-language ${className}`}>
    <Globe size={17} aria-hidden="true" />
    <select className={compact ? 'is-compact' : undefined} aria-label="Ngôn ngữ giao diện" value={i18n.language.slice(0, 2)}
      onChange={event => void setAppLanguage(event.target.value as SupportedLanguage)}>
      {languages.map(([code, name]) => <option value={code} key={code}>{compact ? code.toUpperCase() : name}</option>)}
    </select>
  </label>;
}
