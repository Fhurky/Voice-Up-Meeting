import {useEffect, useState, type FormEvent} from 'react';
import {Navigate, useNavigate} from 'react-router';
import {useAuth} from '@/contexts/AuthContext';
import {useIntl} from '@/contexts/IntlContext';
import {ApiError} from '@/lib/apiClient';
import {AuthService} from '@/services/auth';

export default function LoginPage() {
  const {user, login, loginAsAdmin} = useAuth();
  const {locale, setLocale, t} = useIntl();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<'password' | 'admin' | null>(null);
  const [localAdminEnabled, setLocalAdminEnabled] = useState(false);
  const title = t('login.title');
  useEffect(() => { document.title = `${title} · VoiceUp`; }, [title]);
  useEffect(() => {
    let active = true;
    void AuthService.options().then((options) => {
      if (active) setLocalAdminEnabled(options.local_admin_login_enabled === true);
    }).catch(() => { /* Password sign-in remains available if discovery fails. */ });
    return () => { active = false; };
  }, []);
  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy('password');
    setError('');
    try {
      await login(username, password);
      navigate('/', {replace: true});
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401 ? 'login.error' : 'login.unavailable');
    } finally {
      setBusy(null);
    }
  }

  async function submitAdmin() {
    if (busy || !localAdminEnabled) return;
    setBusy('admin');
    setError('');
    try {
      await loginAsAdmin();
      navigate('/', {replace: true});
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 404
        ? 'login.adminDisabled'
        : caught instanceof ApiError && caught.code === 'local_admin_unavailable'
          ? 'login.adminUnavailable' : 'login.unavailable');
    } finally {
      setBusy(null);
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
          <button type="submit" disabled={busy !== null}>{busy === 'password' ? t('login.busy') : t('login.submit')}</button>
          {localAdminEnabled && <button className="button-secondary" type="button" disabled={busy !== null} onClick={() => { void submitAdmin(); }}>
            {busy === 'admin' ? t('login.busy') : t('login.admin')}
          </button>}
        </form>
        <button className="language" type="button" onClick={() => setLocale(locale === 'en' ? 'tr' : 'en')}>
          {t('common.otherLanguage')}
        </button>
      </section>
    </main>
  );
}
