import { useState, useEffect } from 'react';
import { useCurrentUser } from './useCurrentUser';
import { supabase } from '../lib/supabase';

interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export function useOrganization() {
  const { user, loading: userLoading } = useCurrentUser();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function getOrganization() {
      if (!user) {
        setOrganization(null);
        setLoading(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('organizations')
          .select('id, name, created_at')
          .eq('id', user.organization_id)
          .single();

        if (error) throw error;

        setOrganization(data);
      } catch (error) {
        console.error('Error fetching organization:', error);
        setOrganization(null);
      } finally {
        setLoading(false);
      }
    }

    getOrganization();
  }, [user]);

  return { organization, loading: loading || userLoading };
}