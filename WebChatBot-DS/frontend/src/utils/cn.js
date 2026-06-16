/**
 * Utility to conditionally join classNames.
 * Usage: cn('base-class', condition && 'conditional-class', 'always-class')
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}
