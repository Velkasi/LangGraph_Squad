export interface AppUser {
  id: string;
  authUid: string;
  orgId: string;
  role: UserRole;
  fullName: string;
  email: string;
}

export interface Patient {
  id: string;
  orgId: string;
  userId: string;
  practitionerId: string;
  fullName?: string;
  email?: string;
}

export interface Practitioner {
  id: string;
  orgId: string;
  userId: string;
  specialty?: string;
  role: UserRole;
}

export type UserRole = 'ADMIN' | 'PRACTITIONER' | 'PATIENT';