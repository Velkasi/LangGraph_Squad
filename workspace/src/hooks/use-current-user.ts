import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { AppUser } from '../types/user';

interface UseCurrentUserReturn {
  user: AppUser | null;
  loading: boolean;
  error: string | null;
}

export const useCurrentUser = (): UseCurrentUserReturn => {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session?.user) {
          setUser(null);
          return;
        }

        const { data, error: fetchError } = await supabase
          .from('app_users')
          .select('*')
          .eq('auth_uid', session.user.id)
          .single();

        if (fetchError) throw fetchError;

        setUser(data as AppUser);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  return { user, loading, error };
};