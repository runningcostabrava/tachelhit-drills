import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import MobileDrillCreator from './MobileDrillCreator';
import { hasIdentity } from '../config';
import { toast } from '../toast';

// Afegir una frase a la biblioteca, des de qualsevol pantalla.
//
// L'amo: «falta un símbol + gran per crear un nou drill». El creador ja existia, però vivia a
// dins de la graella de drills, darrere d'un menú: qui obria l'app i volia posar-hi una frase
// que acabava de sentir havia de saber on era.
//
// Aquí és una pàgina seva (`/afegeix`), i el + de la portada i del menú hi porten. Quan la frase
// és feta, es torna a la biblioteca, que és on apareix.

export default function AddSentencePage() {
  const navigate = useNavigate();

  useEffect(() => {
    document.title = 'Afegeix una frase · Tamazight';
    if (!hasIdentity()) {
      toast.error('Per afegir una frase et cal un nom: fes-te’n un al perfil.');
      navigate('/signin');
    }
  }, [navigate]);

  if (!hasIdentity()) return null;

  return (
    <MobileDrillCreator onClose={() => navigate(-1)}
                        onDrillCreated={() => { toast.success('Afegida a la biblioteca'); navigate('/drills'); }} />
  );
}
