import {useEffect, useState, type FormEvent} from 'react';
import {Navigate, useNavigate} from 'react-router';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';
import {ApiError} from '@/lib/apiClient';

export default function LoginPage() {
  const {user, login} = useAuth();
  const {locale, setLocale, t} = useIntl();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const title = t('login.title');
  useEffect(() => { document.title = `${title} · VoiceUp`; }, [title]);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username, password);
      navigate('/', {replace: true});
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401 ? 'login.error' : 'login.unavailable');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="eyebrow">{t('speaker.pilot')}</div>
        <h1>{"VoiceUp"}</h1>
        <p>{t('login.subtitle')}</p>
        <form onSubmit={submit}>
          <label htmlFor="username">{t('login.username')}</label>
          <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <label htmlFor="password">{t('login.password')}</label>
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <div role="alert">{t(error)}</div>}
          <button type="submit" disabled={busy}>{busy ? t('login.busy') : t('login.submit')}</button>
        </form>
        <button className="language" type="button" onClick={() => setLocale(locale === 'en' ? 'tr' : 'en')}>
          {t('common.otherLanguage')}
        </button>
      </section>
    </main>
  );
}
