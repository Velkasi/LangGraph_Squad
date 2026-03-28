import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase/client';
import { User } from '../lib/types';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check active session
    const checkUser = async () => {
      const currentUser = await supabase.auth.getUser();
      setUser(currentUser.data?.user ?? null);
      setLoading(false);
    };

    checkUser();

    // Listen for auth changes
    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    return () => {
      listener?.subscription.unsubscribe();
    };
  }, []);

  return { user, loading };
};