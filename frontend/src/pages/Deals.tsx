import { Link, useParams } from 'react-router-dom'

// Placeholder for screen 4 ("Deals"), built in milestone M2.
export function Deals() {
  const { listId } = useParams()
  return (
    <div className="mx-auto max-w-2xl px-4 py-10 text-center">
      <h1 className="text-2xl font-semibold">Deals</h1>
      <p className="mt-2 text-stone-600">Ranking and the cart plan arrive in M2. Your list is saved.</p>
      <Link to={`/lists/${listId}`} className="mt-4 inline-block text-brand-700 hover:underline">
        Back to the list
      </Link>
    </div>
  )
}
