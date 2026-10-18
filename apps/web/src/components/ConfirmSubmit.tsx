"use client";
// A submit button that asks first ("Delete this account?"): the form is sent only when the answer is yes.
export function ConfirmSubmit({ ask, children, className }: { ask: string; children: React.ReactNode; className?: string }) {
  return (
    <button
      type="submit"
      className={className}
      onClick={(e) => {
        if (!window.confirm(ask)) e.preventDefault();
      }}
    >
      {children}
    </button>
  );
}
