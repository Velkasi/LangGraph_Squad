import { Stack, useRouter } from 'expo-router';
import { useCurrentUser } from '../src/hooks/useCurrentUser';
import { useEffect } from 'react';

const RootLayout = () => {
  const { data: user, isLoading } = useCurrentUser();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (user?.role === 'patient') {
        router.replace('/patient');
      } else if (user?.role === 'practitioner') {
        router.replace('/practitioner');
      } else if (user?.role === 'admin') {
        router.replace('/admin');
      } else {
        router.replace('/auth');
      }
    }
  }, [user, isLoading, router]);

  return <Stack />;
};

export default RootLayout;