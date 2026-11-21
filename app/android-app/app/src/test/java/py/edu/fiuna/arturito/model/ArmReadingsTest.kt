package py.edu.fiuna.arturito.model

import org.junit.Assert.*
import org.junit.Test

class ArmReadingsTest {
    @Test fun decodesPhysicalReferencesAndServoSignals() {
        val arm = requireNotNull(ArmReadings.decode("q=0.00,-5.03,0.02;e=0,4,6;c=010;fc=001;pz=-1;mn=1500"))
        assertEquals(-5.03, arm.joints[1].angleDegrees, 0.0)
        assertEquals(ArmJointState.BRAKED, arm.joints[1].state)
        assertTrue(arm.joints[1].zeroKnown)
        assertFalse(arm.joints[2].zeroKnown)
        assertTrue(arm.joints[2].limitActive)
        assertNull(arm.gripperPulseUs)
        assertEquals(1500, arm.wristPulseUs ?: -1)
    }

    @Test fun malformedJointReadingsStayUnknown() {
        assertNull(ArmReadings.decode(null))
        assertNull(ArmReadings.decode("q=NaN,0,0;e=0,0,0;c=000;fc=000"))
        assertNull(ArmReadings.decode("q=0,0,0;e=0,7,0;c=000;fc=000"))
    }
}
