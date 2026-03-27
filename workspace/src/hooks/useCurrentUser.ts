import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { useRouter } from 'expo-router';

interface User {
  id: string;
  email: string;
  role: 'admin' | 'practitioner' | 'patient';
  organization_id: string;
}

export function useCurrentUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function getUser() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) {
          setUser(null);
          router.replace('/(auth)/login');
          return;
        }

        const { data, error } = await supabase
          .from('users')
          .select('id, email, role, organization_id')
          .eq('auth_uid', session.user.id)
          .single();

        if (error) throw error;

        setUser(data);
      } catch (error) {
        console.error('Error fetching user:', error);
        setUser(null);
        router.replace('/(auth)/login');
      } finally {
        setLoading(false);
      }
    }

    getUser();

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session) {
          setUser(null);
          router.replace('/(auth)/login');
        } else {
          getUser();
        }
      }
    );

    return () => {
      authListener?.subscription.unsubscribe();
    };
  }, [router]);

  return { user, loading };
}