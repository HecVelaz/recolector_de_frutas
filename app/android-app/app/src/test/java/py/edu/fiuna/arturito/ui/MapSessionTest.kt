package py.edu.fiuna.arturito.ui

import org.junit.Assert.*
import org.junit.Test
import py.edu.fiuna.arturito.model.GpsFix

class MapSessionTest {
    @Test fun ignoresOlderGpsSamples() {
        val session = MapSession()
        val current = session.position
        session.accept(GpsFix(current.latitude, current.longitude, current.timestampMillis - 1))
        assertEquals(1, session.track.size)
    }
    @Test fun pausesAndResetsWithoutLeavingPreviousTrail() {
        val session = MapSession()
        session.playing = true
        session.tick()
        assertEquals(2, session.track.size)
        assertTrue(session.distanceMeters > 0)
        session.playing = false
        session.tick()
        assertEquals(2, session.track.size)
        session.reset()
        assertEquals(1, session.track.size)
        assertEquals(0, session.index)
        assertFalse(session.playing)
        assertEquals(0.0, session.distanceMeters, 0.0)
    }
    @Test fun boundsHistoryForLongGpsSessions() {
        val session = MapSession()
        val start = session.position
        repeat(700) { session.accept(start.copy(timestampMillis = start.timestampMillis + it)) }
        assertEquals(600, session.track.size)
    }
}
