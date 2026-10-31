/**
 * Session identity, as the backend reports it.
 *
 * `is_staff` is a HINT for choosing what to render. It is not a permission:
 * every staff-only endpoint enforces its own check server-side, because
 * anything the client is told can be edited by the client.
 */
export interface Identity {
  authenticated: boolean;
  username: string | null;
  is_staff: boolean;
}

export const ANONYMOUS: Identity = {
  authenticated: false,
  username: null,
  is_staff: false,
};
