import {useState, type FormEvent} from 'react';
import {Navigate, useNavigate} from 'react-router';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';

export default function LoginPage() {
  const {user, login} = useAuth();
  const {locale, setLocale, t} = useIntl();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username, password);
      navigate('/', {replace: true});
    } catch {
      setError(t('login.error'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="eyebrow">@@PRIMARY_DOMAIN@@ · platform baseline</div>
        <h1>{@@PRODUCT_NAME_JSON@@}</h1>
        <p>{t('login.subtitle')}</p>
        <form onSubmit={submit}>
          <label htmlFor="username">Username</label>
          <input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <div role="alert">{error}</div>}
          <button type="submit" disabled={busy}>{busy ? t('login.busy') : 'Sign in'}</button>
        </form>
        <button className="language" type="button" onClick={() => setLocale(locale === 'en' ? 'tr' : 'en')}>
          {locale === 'en' ? 'Türkçe' : 'English'}
        </button>
      </section>
    </main>
  );
}
