import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';
import { AppUser, UserRole } from '@/types/user';

interface UseCurrentUserReturn {
  user: AppUser | null;
  role: UserRole | null;
  isLoading: boolean;
  error: Error | null;
}

export function useCurrentUser(): UseCurrentUserReturn {
  const { data, isLoading, error } = useQuery<AppUser | null, Error>({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session?.user) {
        return null;
      }
      
      const { data: userData, error: dbError } = await supabase
        .from('users')
        .select('*')
        .eq('auth_uid', session.user.id)
        .single();
      
      if (dbError) {
        throw dbError;
      }
      
      return userData as AppUser;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });

  return {
    user: data,
    role: data?.role || null,
    isLoading,
    error: error || null,
  };
}