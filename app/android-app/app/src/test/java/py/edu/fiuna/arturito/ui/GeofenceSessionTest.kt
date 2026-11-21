package py.edu.fiuna.arturito.ui

import org.junit.Assert.*
import org.junit.Test
import py.edu.fiuna.arturito.model.FencePoint

class GeofenceSessionTest {
    private val a = FencePoint(-25.33, -57.51)
    private val b = FencePoint(-25.33, -57.509)
    private val c = FencePoint(-25.331, -57.509)
    private val d = FencePoint(-25.331, -57.51)
    private fun square() = GeofenceSession().apply { editing = true; listOf(a, b, c, d).forEach { tap(it, null) } }

    @Test fun crossingPointDoesNotModifyDraft() {
        val session = GeofenceSession().apply { editing = true; listOf(a, c, d).forEach { tap(it, null) } }
        session.tap(b, null)
        assertEquals(listOf(a, c, d), session.vertices.toList())
    }
    @Test fun moveDeleteAndUndoPreserveValidGeometry() {
        val session = square()
        session.close()
        assertTrue(session.canSave)
        session.editing = true
        session.tap(b, 1)
        session.tap(FencePoint(-25.3301, -57.5089), null)
        assertNotEquals(b, session.vertices[1])
        session.undo()
        assertEquals(b, session.vertices[1])
        session.selected = 1
        session.deleteSelected()
        assertEquals(3, session.vertices.size)
        assertTrue(session.closed)
        session.selected = 1
        session.deleteSelected()
        assertFalse(session.closed)
        assertFalse(session.canSave)
    }
    @Test fun editingInvalidatesSavedPayloadAndUndoRestoresIt() {
        val session = square()
        session.close(); session.markSaved()
        assertTrue(session.savedMatches)
        session.reopen()
        assertFalse(session.savedMatches)
        session.undo()
        assertTrue(session.savedMatches)
        session.clear()
        assertNotNull(session.savedJson)
        assertFalse(session.canSave)
        session.undo()
        assertTrue(session.savedMatches)
    }
}
