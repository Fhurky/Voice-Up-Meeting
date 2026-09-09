import {Link} from 'react-router';
import {useIntl} from '@/contexts/IntlContext';
import {useEffect} from 'react';
export default function NotFoundPage() {
  const {t} = useIntl();
  const title = t('common.notFound');
  useEffect(() => { document.title = `${title} · VoiceUp`; }, [title]);
  return <main className="center"><div><h1>{t('common.notFound')}</h1><Link to="/">{t('nav.home')}</Link></div></main>;
}
